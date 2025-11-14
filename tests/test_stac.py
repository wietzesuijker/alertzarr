from autopilot.geozarr import ConversionOutput
from autopilot.stac import build_stac_item


def test_build_stac_item_sets_links() -> None:
    class FakeAlert:
        id = "alert-1"

        class Model:
            description = "Test alert"
            area_of_interest = {
                "type": "Polygon",
                "coordinates": [[[-1, -1], [1, -1], [1, 1], [-1, 1], [-1, -1]]],
            }
            issued = "2025-01-01T00:00:00Z"
            severity = "severe"
            hazard_type = "flood"

        model = Model()

    output = ConversionOutput(
        alert_id="alert-1",
        bucket="bucket",
        key="alerts/flood/alert-1/geozarr-placeholder.json",
        s3_uri="s3://bucket/alerts/flood/alert-1/geozarr-placeholder.json",
        bytes_written=10,
        duration_seconds=0.5,
    )

    item = build_stac_item(FakeAlert(), output, "stac-bucket")
    assert item["assets"]["geozarr"]["href"].startswith("s3://bucket")
    assert item["links"][0]["href"] == "s3://stac-bucket/items/alert-1-geozarr.json"
    assert item["assets"]["geozarr"]["type"] == "application/json"
    assert item["assets"]["geozarr"]["roles"] == ["data"]


def test_build_stac_item_marks_zarr_assets() -> None:
    class FakeAlert:
        id = "alert-1"

        class Model:
            description = "Test alert"
            area_of_interest = {
                "type": "Polygon",
                "coordinates": [[[-1, -1], [1, -1], [1, 1], [-1, 1], [-1, -1]]],
            }
            issued = "2025-01-01T00:00:00Z"
            severity = "severe"
            hazard_type = "flood"

        model = Model()

    output = ConversionOutput(
        alert_id="alert-1",
        bucket="bucket",
        key="alerts/flood/alert-1/geozarr-output.zarr",
        s3_uri="s3://bucket/alerts/flood/alert-1/geozarr-output.zarr",
        bytes_written=10,
        duration_seconds=0.5,
    )

    item = build_stac_item(FakeAlert(), output, "stac-bucket")
    assert item["assets"]["geozarr"]["type"] == "application/vnd+zarr"
    assert "zarr" in item["assets"]["geozarr"]["roles"]
