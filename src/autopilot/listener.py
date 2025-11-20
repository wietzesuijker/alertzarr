"""Alert feed polling and publication services."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Sequence

import httpx

from .alerts import LoadedAlert, parse_alert_payload
from .state import AlertStateStore

LOGGER = logging.getLogger(__name__)


@dataclass
class AlertFeedSpec:
    """Configuration for a single alert feed."""

    name: str
    url: str

    @classmethod
    def parse(cls, raw: str, index: int) -> "AlertFeedSpec":
        if "=" in raw:
            name, url = raw.split("=", 1)
        elif ":" in raw:
            name, url = raw.split(":", 1)
        else:
            name = f"feed-{index}"
            url = raw
        return cls(name=name.strip() or f"feed-{index}", url=url.strip())


class AlertFeedClient:
    """Fetch alerts from HTTP feeds and normalise payloads."""

    def __init__(self, spec: AlertFeedSpec, timeout_seconds: float = 15.0):
        self.spec = spec
        self.timeout_seconds = timeout_seconds

    async def fetch_alerts(self) -> list[LoadedAlert]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(self.spec.url)
            response.raise_for_status()
            payload = response.json()
        records = _extract_records(payload)
        alerts: list[LoadedAlert] = []
        for record in records:
            try:
                alerts.append(parse_alert_payload(record))
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("Failed to parse alert from %s: %s", self.spec.name, exc)
        return alerts


class AlertListener:
    """Poll feeds, deduplicate alerts, and publish them downstream."""

    def __init__(
        self,
        feeds: Sequence[AlertFeedClient],
        publisher,
        state_store: AlertStateStore,
        poll_seconds: int,
    ) -> None:
        self.feeds = feeds
        self.publisher = publisher
        self.state_store = state_store
        self.poll_seconds = poll_seconds

    async def run_once(self) -> int:
        published = 0
        for feed in self.feeds:
            try:
                alerts = await feed.fetch_alerts()
            except Exception as exc:  # pragma: no cover
                LOGGER.exception("Feed %s failed: %s", feed.spec.name, exc)
                continue
            for alert in alerts:
                if self.state_store.is_new(alert.id):
                    await self.publisher(alert)
                    self.state_store.mark_processed(alert.id)
                    published += 1
        return published

    async def run_forever(self) -> None:
        while True:
            published = await self.run_once()
            LOGGER.info("Processed cycle; published=%s", published)
            await asyncio.sleep(self.poll_seconds)


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [dict(_normalise(record)) for record in payload]
    if isinstance(payload, dict):
        for key in ("alerts", "features", "items", "data"):
            if isinstance(payload.get(key), list):
                return [dict(_normalise(record)) for record in payload[key]]
        return [dict(_normalise(payload))]
    return []


def _normalise(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        return {}
    if "properties" in record and isinstance(record["properties"], dict):
        merged = dict(record["properties"])
        if record.get("geometry"):
            merged.setdefault("areaOfInterest", record["geometry"])
        return merged
    return record
