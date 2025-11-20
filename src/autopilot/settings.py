"""Configuration settings for AlertZarr."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    alert_exchange: str = "autopilot.alerts"
    alert_routing_key: str = "alerts.disaster.flood"

    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "autopilot"
    minio_secret_key: str = "autopilot123"
    minio_region: str = "us-east-1"
    geozarr_bucket: str = "autopilot-geozarr"
    stac_bucket: str = "autopilot-stac"
    stac_public_base_url: str = "http://localhost:7000/stac"
    real_conversion_enabled: bool = False
    converter_output_prefix: str = "alerts"
    converter_collection: str = "sentinel-2-l2a"
    converter_groups: list[str] = Field(
        default_factory=lambda: [
            "/measurements/reflectance/r10m",
            "/measurements/reflectance/r20m",
            "/measurements/reflectance/r60m",
            "/quality/l2a_quicklook/r10m",
        ]
    )
    converter_spatial_chunk: int = 1024
    converter_min_dimension: int = 256
    converter_tile_width: int = 256
    converter_enable_sharding: bool = True
    eodc_stac_api: str = "https://stac.core.eopf.eodc.eu"
    eodc_collection: str = "sentinel-2-l2a"
    eodc_cloud_cover: int = 40
    eodc_results_limit: int = 3
    eodc_days_lookback: int = 10
    eodc_s3_endpoint: str = "https://s3.de.io.cloud.ovh.net"
    eodc_s3_region: str = "gra"
    eodc_zarr_asset_keys: list[str] = Field(default_factory=lambda: ["product", "zarr"])
    titiler_base_url: str = "http://localhost:8080"
    titiler_tile_matrix_set: str = "WebMercatorQuad"
    metrics_path: str = "local/metrics.jsonl"

    alert_feed_specs_raw: str = Field(default="", alias="ALERT_FEED_SPECS")
    alert_listener_poll_seconds: int = 300
    alert_listener_state_path: str = "local/listener_state.json"

    workflow_trigger_state_path: str = "local/workflow_state.json"
    argo_base_url: str | None = None
    argo_namespace: str = "default"
    argo_workflow_template: str = "geozarr-auto-pilot"
    argo_service_account_token: str | None = None
    workflow_submit_timeout_seconds: float = 30.0

    @model_validator(mode="after")
    def _require_external_endpoints(self) -> "Settings":
        for attr in ("titiler_base_url", "stac_public_base_url"):
            value = getattr(self, attr)
            if not value or not str(value).strip():
                raise ValueError(f"{attr} must be configured")
        # normalise filesystem paths
        self.metrics_path = str(Path(self.metrics_path))
        self.alert_listener_state_path = str(Path(self.alert_listener_state_path))
        self.workflow_trigger_state_path = str(Path(self.workflow_trigger_state_path))
        return self

    @property
    def alert_feed_specs(self) -> list[str]:
        return _split_feed_specs(self.alert_feed_specs_raw)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def _split_feed_specs(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    raise TypeError("alert_feed_specs must be a comma-delimited string or list")
