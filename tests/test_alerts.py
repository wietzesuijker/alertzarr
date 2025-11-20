from pathlib import Path

from autopilot.alerts import load_alert, parse_alert_payload

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "sample_alerts"


def test_load_alert_parses_core_fields() -> None:
    alert = load_alert(SAMPLES / "copernicus_flood.json")

    assert alert.id == "COP_EMS_2025_004211"
    assert alert.model.hazard_type == "flood"
    assert alert.model.area_of_interest["type"] == "Polygon"


def test_parse_alert_payload_handles_variants() -> None:
    alert = parse_alert_payload(
        {
            "alertId": "GDACS-1",
            "title": "Flood warning",
            "severityLevel": "moderate",
            "hazard_type": "flood",
            "sent": "2025-01-02T00:00:00Z",
            "properties": {"ignored": True},
            "source": {"name": "GDACS", "url": "https://gdacs.org"},
            "geometry": {
                "type": "Point",
                "coordinates": [0, 0],
            },
        }
    )

    assert alert.id == "GDACS-1"
    assert alert.model.severity == "moderate"
    assert alert.model.hazard_type == "flood"
    assert alert.model.area_of_interest["type"] == "Point"
