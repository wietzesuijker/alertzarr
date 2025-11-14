"""Placeholder GeoZarr conversion logic used by the local pipeline."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from aiobotocore.session import get_session

from .alerts import LoadedAlert
from .catalog import SceneSummary, fetch_recent_scenes
from .settings import get_settings


@dataclass
class ConversionOutput:
    alert_id: str
    bucket: str
    key: str
    s3_uri: str
    bytes_written: int
    duration_seconds: float
    scenes: list[SceneSummary] = field(default_factory=list)


async def simulate_conversion(
    alert: LoadedAlert,
    include_scene_search: bool = True,
) -> ConversionOutput:
    start = time.perf_counter()
    session = get_session()
    settings = get_settings()

    key = f"alerts/{alert.model.hazard_type}/{alert.id}/geozarr-placeholder.json"
    scenes: list[SceneSummary] = []
    if include_scene_search:
        scenes = await fetch_recent_scenes(alert)
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
        scenes=scenes,
    )
