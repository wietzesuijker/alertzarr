"""Utilities for discovering real Sentinel-2 scenes that overlap an alert AOI."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import httpx

from .alerts import LoadedAlert

LOGGER = logging.getLogger(__name__)
EARTH_SEARCH_URL = "https://earth-search.aws.element84.com/v1/search"
DEFAULT_COLLECTIONS = ["sentinel-2-l2a"]


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

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "collection": self.collection,
            "datetime": self.datetime,
            "cloud_cover": self.cloud_cover,
            "preview_href": self.preview_href,
            "data_href": self.data_href,
            "stac_item_href": self.stac_item_href,
        }


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


async def fetch_recent_scenes(
    alert: LoadedAlert,
    *,
    limit: int = 2,
    cloud_cover: int = 40,
    collections: Iterable[str] | None = None,
    client: httpx.AsyncClient | None = None,
) -> list[SceneSummary]:
    """Query Earth-Search for Sentinel-2 scenes intersecting the alert AOI."""

    issued = _parse_datetime(alert.model.issued)
    start = _format_datetime(issued - timedelta(days=7))
    end = _format_datetime(issued + timedelta(days=1))

    payload: dict[str, Any] = {
        "collections": list(collections or DEFAULT_COLLECTIONS),
        "intersects": alert.model.area_of_interest,
        "limit": limit,
        "datetime": f"{start}/{end}",
        "sortby": [
            {"field": "properties.datetime", "direction": "desc"},
        ],
        "query": {
            "eo:cloud_cover": {"lt": cloud_cover},
        },
    }

    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        close_client = True

    try:
        response = await client.post(EARTH_SEARCH_URL, json=payload)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:  # pragma: no cover - network failure handled gracefully
        LOGGER.warning("Unable to fetch Sentinel scenes: %s", exc)
        return []
    finally:
        if close_client:
            await client.aclose()

    scenes: list[SceneSummary] = []
    for feature in data.get("features", []):
        assets = feature.get("assets", {})
        preview = (
            assets.get("thumbnail")
            or assets.get("overview")
            or assets.get("preview")
            or {}
        ).get("href")
        data_asset = (
            assets.get("visual")
            or assets.get("true_color")
            or assets.get("B04")
            or assets.get("granule")
        )
        data_href = (data_asset or {}).get("href")

        scenes.append(
            SceneSummary(
                id=feature.get("id", "unknown"),
                collection=feature.get("collection", DEFAULT_COLLECTIONS[0]),
                datetime=feature.get("properties", {}).get(
                    "datetime", issued.isoformat()
                ),
                cloud_cover=feature.get("properties", {}).get("eo:cloud_cover"),
                preview_href=preview,
                data_href=data_href,
                stac_item_href=(
                    "https://earth-search.aws.element84.com/v1/collections/"
                    f"{feature.get('collection', DEFAULT_COLLECTIONS[0])}/items/"
                    f"{feature.get('id', 'unknown')}"
                ),
            )
        )

    return scenes


__all__ = ["SceneSummary", "fetch_recent_scenes"]
