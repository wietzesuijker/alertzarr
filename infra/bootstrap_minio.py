"""Seed MinIO buckets required for the MVP."""
from __future__ import annotations

import asyncio
import logging
import os

from aiobotocore.session import get_session

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "autopilot")
SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "autopilot123")
REGION = os.getenv("MINIO_REGION", "us-east-1")

BUCKETS = [
    "autopilot-alerts",
    "autopilot-geozarr",
    "autopilot-stac",
]


async def ensure_bucket(s3_client, bucket: str) -> None:
    LOGGER.info("Ensuring bucket %s", bucket)
    existing = await s3_client.list_buckets()
    names = {b["Name"] for b in existing.get("Buckets", [])}
    if bucket in names:
        LOGGER.info("Bucket %s already exists", bucket)
        return
    await s3_client.create_bucket(Bucket=bucket)
    LOGGER.info("Bucket %s created", bucket)


async def main() -> None:
    session = get_session()
    async with session.create_client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name=REGION,
    ) as s3:
        for bucket in BUCKETS:
            await ensure_bucket(s3, bucket)


if __name__ == "__main__":
    asyncio.run(main())
