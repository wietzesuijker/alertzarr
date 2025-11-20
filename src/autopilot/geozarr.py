"""GeoZarr conversion logic for AlertZarr."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

import boto3
import xarray as xr
from aiobotocore.session import get_session
from eopf_geozarr import create_geozarr_dataset
from eopf_geozarr.conversion.fs_utils import get_storage_options

from .alerts import LoadedAlert
from .catalog import SceneSummary, fetch_eodc_scenes
from .settings import get_settings

LOGGER = logging.getLogger(__name__)


@dataclass
class ViewerLinks:
    collection_id: str
    item_id: str
    base_url: str
    tile_matrix_set: str
    viewer_url: str
    tilejson_url: str
    info_url: str


@dataclass
class ConversionOutput:
    alert_id: str
    bucket: str
    key: str
    s3_uri: str
    bytes_written: int
    duration_seconds: float
    collection_id: str | None = None
    item_id: str | None = None
    scenes: list[SceneSummary] = field(default_factory=list)
    viewer: ViewerLinks | None = None


ConversionMode = Literal["auto", "real", "simulate"]


async def convert_alert(
    alert: LoadedAlert,
    include_scene_search: bool = True,
    mode: ConversionMode = "auto",
) -> ConversionOutput:
    """Convert an alert to GeoZarr, optionally falling back to a placeholder."""

    settings = get_settings()
    if mode in {"auto", "real"} and settings.real_conversion_enabled:
        real_output = await _attempt_real_conversion(alert)
        if real_output is not None:
            return real_output
        if mode == "real":
            raise RuntimeError("Real conversion requested but no scenes were available")
        LOGGER.info("Falling back to placeholder conversion")

    return await simulate_conversion(alert, include_scene_search=include_scene_search)


async def simulate_conversion(
    alert: LoadedAlert,
    include_scene_search: bool = True,
) -> ConversionOutput:
    start = time.perf_counter()
    session = get_session()
    settings = get_settings()

    collection_source = alert.model.hazard_type or settings.converter_collection
    collection_id = _slugify(collection_source)
    item_id = _slugify(f"{alert.id}-placeholder")
    key = f"alerts/{alert.model.hazard_type}/{alert.id}/geozarr-placeholder.json"
    scenes: list[SceneSummary] = []
    if include_scene_search:
        scenes = await fetch_eodc_scenes(alert, limit=2)
    payload: dict[str, object] = {
        "alert_id": alert.id,
        "hazard": alert.model.hazard_type,
        "description": alert.model.description,
        "aoi": alert.model.area_of_interest,
        "notes": "Placeholder dataset produced by the local AlertZarr pipeline.",
    }

    if scenes:
        payload["source_scenes"] = [scene.as_dict() for scene in scenes]

    async with session.create_client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        region_name=settings.minio_region,
    ) as s3:
        await s3.put_object(
            Bucket=settings.geozarr_bucket,
            Key=key,
            Body=json.dumps(payload).encode("utf-8"),
            ContentType="application/json",
        )

    duration = time.perf_counter() - start

    return ConversionOutput(
        alert_id=alert.id,
        bucket=settings.geozarr_bucket,
        key=key,
        s3_uri=f"s3://{settings.geozarr_bucket}/{key}",
        bytes_written=len(json.dumps(payload)),
        duration_seconds=duration,
        collection_id=collection_id,
        item_id=item_id,
        scenes=scenes,
    )


async def _attempt_real_conversion(alert: LoadedAlert) -> ConversionOutput | None:
    settings = get_settings()
    scenes = await fetch_eodc_scenes(alert)
    candidate_scenes = [scene for scene in scenes if scene.zarr_href]
    if not candidate_scenes:
        LOGGER.info("EODC search returned no scenes with Zarr assets")
        return None

    selected = sorted(candidate_scenes, key=_scene_sort_key, reverse=True)[0]
    start = time.perf_counter()
    (
        output_uri,
        key,
        bytes_written,
        collection_id,
        item_id,
    ) = await asyncio.to_thread(_convert_scene, alert, selected, settings)
    duration = time.perf_counter() - start
    viewer = _build_viewer_links(settings, collection_id, item_id)
    return ConversionOutput(
        alert_id=alert.id,
        bucket=settings.geozarr_bucket,
        key=key,
        s3_uri=output_uri,
        bytes_written=bytes_written,
        duration_seconds=duration,
        collection_id=collection_id,
        item_id=item_id,
        scenes=[selected],
        viewer=viewer,
    )


def _convert_scene(
    alert: LoadedAlert, scene: SceneSummary, settings
) -> tuple[str, str, int, str, str]:
    if not scene.zarr_href:
        raise RuntimeError("Selected scene does not provide a Zarr asset")

    key, collection_id, item_id = _build_output_layout(alert, scene, settings)
    output_uri = f"s3://{settings.geozarr_bucket}/{key}"
    source_storage = get_storage_options(
        scene.zarr_href,
        anon=True,
        endpoint_url=settings.eodc_s3_endpoint,
        client_kwargs={
            "endpoint_url": settings.eodc_s3_endpoint,
            "region_name": settings.eodc_s3_region,
        },
    )

    LOGGER.info("Loading source Zarr: %s", scene.zarr_href)
    datatree = xr.open_datatree(
        scene.zarr_href,
        engine="zarr",
        chunks="auto",
        storage_options=source_storage,
    )

    with _aws_env(
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        region=settings.minio_region,
        endpoint=settings.minio_endpoint,
    ):
        create_geozarr_dataset(
            dt_input=datatree,
            groups=settings.converter_groups,
            output_path=output_uri,
            spatial_chunk=settings.converter_spatial_chunk,
            min_dimension=settings.converter_min_dimension,
            tile_width=settings.converter_tile_width,
            enable_sharding=settings.converter_enable_sharding,
        )

    bytes_written = _calculate_total_size(settings.geozarr_bucket, key, settings)
    LOGGER.info("GeoZarr written to %s (%s bytes)", output_uri, bytes_written)
    return output_uri, key, bytes_written, collection_id, item_id


def _build_output_layout(
    alert: LoadedAlert, scene: SceneSummary, settings
) -> tuple[str, str, str]:
    collection_raw = alert.model.hazard_type or settings.converter_collection
    collection_id = _slugify(collection_raw)
    slug = _slugify(f"{alert.id}-{scene.id}")
    prefix = settings.converter_output_prefix.strip("/")
    parts = [part for part in (prefix, collection_id) if part]
    key_prefix = "/".join(parts) if parts else collection_id
    key = f"{key_prefix}/{slug}.zarr"
    return key, collection_id, slug


def _build_viewer_links(
    settings, collection_id: str, item_id: str
) -> ViewerLinks | None:
    if not settings.titiler_base_url:
        return None
    base_url = settings.titiler_base_url.rstrip("/")
    tile_matrix = settings.titiler_tile_matrix_set
    root = f"{base_url}/collections/{collection_id}/items/{item_id}"
    return ViewerLinks(
        collection_id=collection_id,
        item_id=item_id,
        base_url=base_url,
        tile_matrix_set=tile_matrix,
        viewer_url=f"{root}/viewer",
        tilejson_url=f"{root}/{tile_matrix}/tilejson.json",
        info_url=f"{root}/info",
    )


_SLUG_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def _slugify(value: str) -> str:
    text = str(value).strip()
    if not text:
        return "artifact"
    cleaned = _SLUG_PATTERN.sub("-", text)
    cleaned = cleaned.strip("-")
    return cleaned or "artifact"


def _calculate_total_size(bucket: str, key: str, settings) -> int:
    client = boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        region_name=settings.minio_region,
    )
    paginator = client.get_paginator("list_objects_v2")
    total = 0
    for page in paginator.paginate(Bucket=bucket, Prefix=key):
        for item in page.get("Contents", []):
            total += int(item.get("Size", 0))
    return total


@contextmanager
def _aws_env(
    *,
    access_key: str,
    secret_key: str,
    region: str,
    endpoint: str,
):
    previous = {
        "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID"),
        "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY"),
        "AWS_DEFAULT_REGION": os.environ.get("AWS_DEFAULT_REGION"),
        "AWS_ENDPOINT_URL": os.environ.get("AWS_ENDPOINT_URL"),
    }
    os.environ["AWS_ACCESS_KEY_ID"] = access_key
    os.environ["AWS_SECRET_ACCESS_KEY"] = secret_key
    os.environ["AWS_DEFAULT_REGION"] = region
    os.environ["AWS_ENDPOINT_URL"] = endpoint
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _scene_sort_key(scene: SceneSummary) -> tuple[datetime, float]:
    try:
        dt = datetime.fromisoformat(scene.datetime.replace("Z", "+00:00"))
    except ValueError:
        dt = datetime.utcnow().replace(tzinfo=timezone.utc)
    cover = scene.cloud_cover if scene.cloud_cover is not None else 100.0
    return (dt, cover)
