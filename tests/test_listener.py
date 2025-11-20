from autopilot.listener import AlertFeedSpec, _extract_records


def test_alert_feed_spec_parse() -> None:
    spec = AlertFeedSpec.parse("copernicus:https://alerts.test/cop", 1)
    assert spec.name == "copernicus"
    assert spec.url == "https://alerts.test/cop"


def test_extract_records_handles_geojson() -> None:
    payload = {
        "features": [
            {
                "properties": {
                    "id": "GDACS-1",
                    "title": "Flood",
                    "hazardType": "flood",
                },
                "geometry": {"type": "Point", "coordinates": [0, 0]},
            }
        ]
    }
    records = _extract_records(payload)
    assert records[0]["title"] == "Flood"
    assert records[0]["areaOfInterest"]["type"] == "Point"
