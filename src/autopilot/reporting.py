"""Run reporting helpers."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .alerts import LoadedAlert
from .geozarr import ConversionOutput


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
        self.steps["alert"] = {
            "id": alert.id,
            "issued": alert.model.issued,
            "hazard": alert.model.hazard_type,
            "severity": alert.model.severity,
        }

    def record_event_publish(self) -> None:
        self.steps["event"] = {"status": "published"}

    def record_conversion(self, output: ConversionOutput) -> None:
        self.steps["conversion"] = {
            "s3_uri": output.s3_uri,
            "duration_seconds": round(output.duration_seconds, 2),
            "bytes_written": output.bytes_written,
        }

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
