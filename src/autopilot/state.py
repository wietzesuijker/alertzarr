"""Persistent alert state tracking utilities."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Iterable


class AlertStateStore:
    """Lightweight JSON-backed set of processed alert identifiers."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = Lock()
        self._seen: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        seen = data.get("alerts", []) if isinstance(data, dict) else []
        self._seen = {str(value) for value in seen}

    def mark_processed(self, alert_id: str) -> None:
        with self._lock:
            self._seen.add(str(alert_id))
            self._persist()

    def extend(self, alert_ids: Iterable[str]) -> None:
        with self._lock:
            for alert_id in alert_ids:
                self._seen.add(str(alert_id))
            self._persist()

    def is_new(self, alert_id: str) -> bool:
        return str(alert_id) not in self._seen

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"alerts": sorted(self._seen)}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
