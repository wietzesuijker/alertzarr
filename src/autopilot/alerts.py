"""Alert ingestion and normalisation utilities."""
from __future__ import annotations

import json
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

    model = Alert(
        id=payload["id"],
        title=payload["title"],
        description=payload["description"],
        issued=payload["issued"],
        severity=payload.get("severity", "unknown"),
        hazard_type=payload.get("hazardType", "unknown"),
        source_name=payload.get("source", {}).get("name", "unknown"),
        source_url=payload.get("source", {}).get("url", ""),
        area_of_interest=payload.get("areaOfInterest", {}),
        parameters=payload.get("parameters", {}),
    )

    return LoadedAlert(id=model.id, raw=payload, model=model)
