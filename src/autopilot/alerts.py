"""Alert ingestion and normalisation utilities."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class Alert(BaseModel):
    id: str
    title: str
    description: str
    issued: str
    severity: str
    hazard_type: str
    source_name: str
    source_url: str
    area_of_interest: dict[str, Any]
    parameters: dict[str, Any]


@dataclass
class LoadedAlert:
    id: str
    raw: dict[str, Any]
    model: Alert


def load_alert(path: Path) -> LoadedAlert:
    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)

    return parse_alert_payload(payload)


def parse_alert_payload(payload: Mapping[str, Any]) -> LoadedAlert:
    if not isinstance(payload, Mapping):
        raise TypeError("Alert payload must be a mapping")

    source = payload.get("source") or {}
    parameters = payload.get("parameters") or {}
    hazard = (
        payload.get("hazardType")
        or payload.get("hazard_type")
        or parameters.get("hazard")
        or parameters.get("hazardType")
        or "unknown"
    )
    severity = (
        payload.get("severity")
        or parameters.get("severity")
        or payload.get("severityLevel")
        or "unknown"
    )
    issued = (
        payload.get("issued")
        or payload.get("time")
        or payload.get("sent")
        or payload.get("updated")
        or ""
    )
    geometry = (
        payload.get("areaOfInterest")
        or payload.get("geometry")
        or parameters.get("geometry")
        or {}
    )
    alert_id = str(
        payload.get("id")
        or payload.get("alertId")
        or payload.get("identifier")
        or parameters.get("id")
        or parameters.get("alertId")
        or "alert"
    )

    model = Alert(
        id=alert_id,
        title=str(payload.get("title") or parameters.get("title") or alert_id),
        description=str(
            payload.get("description") or parameters.get("description") or ""
        ),
        issued=str(issued),
        severity=str(severity),
        hazard_type=str(hazard),
        source_name=str(
            source.get("name") or parameters.get("source_name") or "unknown"
        ),
        source_url=str(source.get("url") or parameters.get("source_url") or ""),
        area_of_interest=geometry,
        parameters=dict(parameters),
    )

    return LoadedAlert(id=model.id, raw=dict(payload), model=model)
