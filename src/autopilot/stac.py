"""STAC item generation for GeoZarr alert outputs."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from aiobotocore.session import get_session
from shapely.geometry import shape

from .alerts import LoadedAlert
from .catalog import SceneSummary
from .geozarr import ConversionOutput
from .settings import get_settings


def build_stac_item(alert: LoadedAlert, output: ConversionOutput, bucket: str) -> dict[str, Any]:
    geometry = alert.model.area_of_interest
    geom = shape(geometry)
    bbox = list(geom.bounds)
    item_id = f"{alert.id}-geozarr"
    now = datetime.utcnow().isoformat() + "Z"
    assets: dict[str, Any] = {
        "geozarr": {
            "href": output.s3_uri,
            "type": "application/json",
            "roles": ["data", "zarr"],
        }
    }
    links: list[dict[str, Any]] = [
        {
            "rel": "self",
            "href": f"s3://{bucket}/items/{item_id}.json",
            "type": "application/json",
        }
    ]

    if output.scenes:
        assets.update(_scene_assets(output.scenes))
        links.extend(_scene_links(output.scenes))

    return {
        "type": "Feature",
        "stac_version": "1.0.0",
        "id": item_id,
        "collection": "alertzarr-disasters",
        "description": alert.model.description,
        "geometry": geometry,
        "bbox": bbox,
        "properties": {
            "datetime": alert.model.issued,
            "created": now,
            "alert:severity": alert.model.severity,
            "alert:hazard": alert.model.hazard_type,
            "source:scene_count": len(output.scenes),
        },
        "assets": assets,
        "links": links,
    }


async def create_stac_item(alert: LoadedAlert, output: ConversionOutput) -> dict[str, Any]:
    settings = get_settings()
    stac_item = build_stac_item(alert, output, settings.stac_bucket)

    session = get_session()
    key = f"items/{stac_item['id']}.json"

    async with session.create_client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        region_name=settings.minio_region,
    ) as s3:
        await s3.put_object(
            Bucket=settings.stac_bucket,
            Key=key,
            Body=json.dumps(stac_item).encode("utf-8"),
            ContentType="application/json",
        )

    return stac_item


def _scene_assets(scenes: list[SceneSummary]) -> dict[str, Any]:
    assets: dict[str, Any] = {}
    for idx, scene in enumerate(scenes, start=1):
        label = f"source-scene-{idx}"
        assets[label] = {
            "href": scene.data_href or scene.stac_item_href,
            "type": "image/tiff; application=geotiff",
            "roles": ["source"],
            "title": f"{scene.collection} {scene.id}",
        }
        if scene.preview_href:
            assets[f"{label}-preview"] = {
                "href": scene.preview_href,
                "type": "image/jpeg",
                "roles": ["preview"],
            }
    return assets


def _scene_links(scenes: list[SceneSummary]) -> list[dict[str, Any]]:
    return [
        {
            "rel": "derived_from",
            "href": scene.stac_item_href,
            "type": "application/json",
            "title": f"{scene.collection}:{scene.id}",
        }
        for scene in scenes
    ]
