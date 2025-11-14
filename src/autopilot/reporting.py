"""Run reporting helpers."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pyproj import Geod
from shapely.geometry import shape

from .alerts import LoadedAlert
from .geozarr import ConversionOutput

GEOD = Geod(ellps="WGS84")


@dataclass
class RunReporter:
    run_id: str | None = None
    started_at: float = field(default=0.0, init=False)
    finished_at: float = field(default=0.0, init=False)
    alert_id: str | None = field(default=None, init=False)
    steps: dict[str, Any] = field(default_factory=dict, init=False)

    def start_run(self) -> None:
        self.run_id = self.run_id or uuid.uuid4().hex
        self.started_at = time.time()

    def record_alert(self, alert: LoadedAlert) -> None:
        self.alert_id = alert.id
        geometry = getattr(alert.model, "area_of_interest", None)
        area_km2 = _area_km2(geometry) if geometry else None
        self.steps["alert"] = {
            "id": alert.id,
            "issued": alert.model.issued,
            "hazard": alert.model.hazard_type,
            "severity": alert.model.severity,
            "area_km2": area_km2,
        }

    def record_event_publish(self) -> None:
        self.steps["event"] = {"status": "published"}

    def record_conversion(self, output: ConversionOutput) -> None:
        self.steps["conversion"] = {
            "s3_uri": output.s3_uri,
            "duration_seconds": round(output.duration_seconds, 2),
            "bytes_written": output.bytes_written,
        }
        if output.scenes:
            self.steps["conversion"].update(
                {
                    "source_scene_ids": [scene.id for scene in output.scenes],
                    "source_scene_count": len(output.scenes),
                    "preview_href": output.scenes[0].preview_href,
                }
            )

    def record_stac_item(self, stac_item: dict[str, Any]) -> None:
        self.steps["stac_item"] = {
            "id": stac_item.get("id"),
            "href": stac_item.get("links", [{}])[0].get("href", ""),
        }

    def finish_run(self) -> None:
        self.finished_at = time.time()

    def summary(self) -> dict[str, Any]:
        if self.finished_at and self.started_at:
            duration = self.finished_at - self.started_at
        else:
            duration = 0.0
        return {
            "run_id": self.run_id,
            "alert_id": self.alert_id,
            "duration_seconds": round(duration, 2),
            "steps": self.steps,
        }

    def persist(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.run_id}.json"
        path.write_text(json.dumps(self.summary(), indent=2), encoding="utf-8")
        return path


def _area_km2(geometry: dict[str, Any]) -> float | None:
    if not geometry:
        return None
    geom = shape(geometry)
    area, _ = GEOD.geometry_area_perimeter(geom)
    return round(abs(area) / 1_000_000, 2)
