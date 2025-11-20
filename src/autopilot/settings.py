"""Configuration settings for AlertZarr."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
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
    stac_public_base_url: str | None = None
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
    titiler_base_url: str | None = None
    titiler_tile_matrix_set: str = "WebMercatorQuad"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
