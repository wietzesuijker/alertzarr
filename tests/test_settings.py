import pytest

from autopilot.settings import Settings


def test_settings_require_titiler_and_stac_urls() -> None:
    settings = Settings(
        titiler_base_url="http://example.com/tiles",
        stac_public_base_url="https://example.com/stac",
        alert_feed_specs_raw="copernicus:https://alerts.test,COP:https://alerts2.test",
    )
    assert settings.titiler_base_url.endswith("/tiles")
    assert settings.stac_public_base_url.endswith("/stac")
    assert settings.alert_feed_specs == [
        "copernicus:https://alerts.test",
        "COP:https://alerts2.test",
    ]


def test_settings_raise_when_missing_urls() -> None:
    with pytest.raises(ValueError):
        Settings(titiler_base_url="", stac_public_base_url="https://example.com/stac")
