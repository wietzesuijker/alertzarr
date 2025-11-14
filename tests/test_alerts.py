from pathlib import Path

from autopilot.alerts import load_alert

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "sample_alerts"


def test_load_alert_parses_core_fields() -> None:
    alert = load_alert(SAMPLES / "copernicus_flood.json")

    assert alert.id == "COP_EMS_2025_001337"
    assert alert.model.hazard_type == "flood"
    assert alert.model.area_of_interest["type"] == "Polygon"
