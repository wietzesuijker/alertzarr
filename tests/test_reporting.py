import json
from pathlib import Path

from autopilot.geozarr import ConversionOutput, ViewerLinks
from autopilot.reporting import RunReporter


def test_run_reporter_tracks_steps() -> None:
    reporter = RunReporter(run_id="test-run")
    reporter.start_run()

    class FakeAlert:
        id = "alert-1"

        class Model:
            issued = "2025-01-01T00:00:00Z"
            hazard_type = "flood"
            severity = "Severe"

        model = Model()

    reporter.record_alert(FakeAlert())
    reporter.record_event_publish()
    viewer = ViewerLinks(
        collection_id="flood",
        item_id="alert-1-S2A",
        base_url="http://localhost:8080",
        tile_matrix_set="WebMercatorQuad",
        viewer_url="http://localhost:8080/collections/flood/items/alert-1-S2A/viewer",
        tilejson_url="http://localhost:8080/collections/flood/items/alert-1-S2A/WebMercatorQuad/tilejson.json",
        info_url="http://localhost:8080/collections/flood/items/alert-1-S2A/info",
    )
    reporter.record_conversion(
        ConversionOutput(
            alert_id="alert-1",
            bucket="bucket",
            key="alerts/flood/alert-1-S2A.zarr",
            s3_uri="s3://bucket/alerts/flood/alert-1-S2A.zarr",
            bytes_written=128,
            duration_seconds=1.23,
            scenes=[],
            viewer=viewer,
        )
    )
    reporter.record_stac_item(
        {"id": "alert-1-geozarr", "links": [{"href": "s3://bucket/item.json"}]}
    )
    reporter.finish_run()

    summary = reporter.summary()
    assert summary["run_id"] == "test-run"
    assert summary["alert_id"] == "alert-1"
    assert summary["steps"]["stac_item"]["id"] == "alert-1-geozarr"
    assert (
        summary["steps"]["conversion"]["viewer"]["viewer_url"]
        == viewer.viewer_url
    )


def test_run_reporter_persist_writes_file(tmp_path: Path) -> None:
    reporter = RunReporter(run_id="persist-test")
    reporter.start_run()

    class FakeAlert:
        id = "alert-2"

        class Model:
            issued = "2025-02-01T00:00:00Z"
            hazard_type = "wildfire"
            severity = "Moderate"
            area_of_interest = {
                "type": "Polygon",
                "coordinates": [[[-1, -1], [1, -1], [1, 1], [-1, 1], [-1, -1]]],
            }

        model = Model()

    reporter.record_alert(FakeAlert())
    reporter.finish_run()
    output_path = reporter.persist(tmp_path)

    assert output_path.exists()
    data = json.loads(output_path.read_text())
    assert data["run_id"] == "persist-test"
    assert data["steps"]["alert"]["id"] == "alert-2"
