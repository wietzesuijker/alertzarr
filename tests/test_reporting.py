from autopilot.geozarr import ConversionOutput
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
    reporter.record_conversion(
        ConversionOutput(
            alert_id="alert-1",
            bucket="bucket",
            key="alerts/flood/alert-1/geozarr-placeholder.json",
            s3_uri="s3://bucket/alerts/flood/alert-1/geozarr-placeholder.json",
            bytes_written=128,
            duration_seconds=1.23,
        )
    )
    reporter.record_stac_item({"id": "alert-1-geozarr", "links": [{"href": "s3://bucket/item.json"}]})
    reporter.finish_run()

    summary = reporter.summary()
    assert summary["run_id"] == "test-run"
    assert summary["alert_id"] == "alert-1"
    assert summary["steps"]["stac_item"]["id"] == "alert-1-geozarr"
