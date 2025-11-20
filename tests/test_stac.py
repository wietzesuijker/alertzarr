from autopilot.geozarr import ConversionOutput, ViewerLinks
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
        collection_id="flood",
        item_id="alert-1-placeholder",
    )

    item = build_stac_item(FakeAlert(), output, "stac-bucket")
    assert item["collection"] == "flood"
    assert item["assets"]["geozarr"]["href"].startswith("s3://bucket")
    assert item["links"][0]["href"] == "s3://stac-bucket/items/alert-1-placeholder.json"
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

    viewer = ViewerLinks(
        collection_id="flood",
        item_id="alert-1-S2A",
        base_url="http://localhost:8080",
        tile_matrix_set="WebMercatorQuad",
        viewer_url="http://localhost:8080/collections/flood/items/alert-1-S2A/viewer",
        tilejson_url="http://localhost:8080/collections/flood/items/alert-1-S2A/WebMercatorQuad/tilejson.json",
        info_url="http://localhost:8080/collections/flood/items/alert-1-S2A/info",
    )

    output = ConversionOutput(
        alert_id="alert-1",
        bucket="bucket",
        key="alerts/flood/alert-1-S2A.zarr",
        s3_uri="s3://bucket/alerts/flood/alert-1-S2A.zarr",
        bytes_written=10,
        duration_seconds=0.5,
        viewer=viewer,
    )

    item = build_stac_item(FakeAlert(), output, "stac-bucket")
    assert item["assets"]["geozarr"]["type"] == "application/vnd+zarr"
    assert "zarr" in item["assets"]["geozarr"]["roles"]
    assert item["assets"]["viewer"]["href"] == viewer.viewer_url
    assert any(link["rel"] == "tilejson" for link in item["links"])


def test_build_stac_item_uses_public_base_url_for_links() -> None:
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
        collection_id="flood",
        item_id="alert-1-placeholder",
    )

    item = build_stac_item(
        FakeAlert(),
        output,
        "stac-bucket",
        public_base_url="https://data.example.com/stac",
    )
    hrefs = {link["rel"]: link["href"] for link in item["links"]}
    assert (
        hrefs["self"] == "https://data.example.com/stac/items/alert-1-placeholder.json"
    )
    assert hrefs["collection"] == "https://data.example.com/stac/collections/flood.json"
