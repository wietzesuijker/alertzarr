"""Utilities for discovering real Sentinel-2 scenes that overlap an alert AOI."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from .alerts import LoadedAlert
from .settings import get_settings

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SceneSummary:
    """Metadata describing an up-to-date Sentinel scene used for context."""

    id: str
    collection: str
    datetime: str
    cloud_cover: float | None
    preview_href: str | None
    data_href: str | None
    stac_item_href: str
    zarr_href: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "id": self.id,
            "collection": self.collection,
            "datetime": self.datetime,
            "cloud_cover": self.cloud_cover,
            "preview_href": self.preview_href,
            "data_href": self.data_href,
            "stac_item_href": self.stac_item_href,
        }
        if self.zarr_href:
            payload["zarr_href"] = self.zarr_href
        return payload


def _parse_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _format_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return (
        value.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


__all__ = ["SceneSummary", "fetch_eodc_scenes"]


async def fetch_eodc_scenes(
    alert: LoadedAlert,
    *,
    limit: int | None = None,
    client: httpx.AsyncClient | None = None,
) -> list[SceneSummary]:
    """Query the EODC STAC API for Sentinel scenes with accessible Zarr assets."""

    settings = get_settings()
    issued = _parse_datetime(alert.model.issued)
    start = _format_datetime(issued - timedelta(days=settings.eodc_days_lookback))
    end = _format_datetime(issued + timedelta(days=1))
    body: dict[str, Any] = {
        "collections": [settings.eodc_collection],
        "intersects": alert.model.area_of_interest,
        "limit": limit or settings.eodc_results_limit,
        "datetime": f"{start}/{end}",
        "query": {
            "eo:cloud_cover": {"lt": settings.eodc_cloud_cover},
        },
        "sortby": [
            {"field": "properties.datetime", "direction": "desc"},
        ],
    }

    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        close_client = True

    try:
        response = await client.post(
            f"{settings.eodc_stac_api.rstrip('/')}/search", json=body
        )
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover - network issues handled gracefully
        LOGGER.warning("Unable to fetch EODC scenes: %s", exc)
        return []
    finally:
        if close_client:
            await client.aclose()

    scenes: list[SceneSummary] = []
    for feature in response.json().get("features", []):
        assets: dict[str, Any] = feature.get("assets", {})
        zarr_href = _select_zarr_asset(assets, settings.eodc_zarr_asset_keys)
        if not zarr_href:
            continue
        preview = (
            assets.get("thumbnail")
            or assets.get("overview")
            or assets.get("preview")
            or {}
        ).get("href")
        data_asset = (
            assets.get("visual") or assets.get("true_color") or assets.get("B04")
        )
        data_href = (data_asset or {}).get("href")

        stac_href = _find_self_href(feature.get("links", []))
        if not stac_href:
            stac_href = (
                f"{settings.eodc_stac_api.rstrip('/')}/collections/"
                f"{feature.get('collection', settings.eodc_collection)}/items/"
                f"{feature.get('id', 'unknown')}"
            )

        scenes.append(
            SceneSummary(
                id=feature.get("id", "unknown"),
                collection=feature.get("collection", settings.eodc_collection),
                datetime=feature.get("properties", {}).get(
                    "datetime", issued.isoformat()
                ),
                cloud_cover=feature.get("properties", {}).get("eo:cloud_cover"),
                preview_href=preview,
                data_href=data_href,
                stac_item_href=stac_href,
                zarr_href=zarr_href,
            )
        )

    return scenes


def _select_zarr_asset(assets: dict[str, Any], priorities: list[str]) -> str | None:
    for key in priorities:
        if (asset := assets.get(key)) and asset.get("href", "").endswith(".zarr"):
            return str(asset["href"])
    for candidate in assets.values():
        href = candidate.get("href")
        if isinstance(href, str) and ".zarr" in href:
            return href
    return None


def _find_self_href(links: list[dict[str, Any]]) -> str | None:
    for link in links:
        if link.get("rel") == "self" and isinstance(link.get("href"), str):
            return link["href"]
    return None
