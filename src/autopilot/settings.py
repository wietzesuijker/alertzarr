"""Configuration settings for AlertZarr."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    alert_exchange: str = "autopilot.alerts"
    alert_routing_key: str = "alerts.disaster.flood"

    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "autopilot"
    minio_secret_key: str = "autopilot123"
    minio_region: str = "us-east-1"
    geozarr_bucket: str = "autopilot-geozarr"
    stac_bucket: str = "autopilot-stac"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
