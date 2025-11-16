"""CI helper for downloading STAC items from MinIO/S3."""

from __future__ import annotations

import argparse
import os
import pathlib
import sys

import boto3


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download STAC JSON objects from a bucket prefix into a directory",
    )
    parser.add_argument(
        "--dest",
        type=pathlib.Path,
        default=pathlib.Path("artifacts/stac"),
        help="Destination directory for downloaded STAC items",
    )
    parser.add_argument(
        "--prefix",
        default=os.environ.get("STAC_PREFIX", "items/"),
        help="Object key prefix to search within the STAC bucket",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    dest: pathlib.Path = args.dest
    dest.mkdir(parents=True, exist_ok=True)

    try:
        endpoint = os.environ["MINIO_ENDPOINT"]
        aws_access_key_id = os.environ["MINIO_ACCESS_KEY"]
        aws_secret_access_key = os.environ["MINIO_SECRET_KEY"]
        region_name = os.environ["MINIO_REGION"]
        bucket = os.environ["STAC_BUCKET"]
    except KeyError as exc:
        missing = exc.args[0]
        raise SystemExit(f"Missing required environment variable: {missing}") from exc

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name,
    )

    downloaded = 0
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=args.prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".json"):
                continue
            target = dest / os.path.basename(key)
            s3.download_file(bucket, key, target.as_posix())
            downloaded += 1

    print(f"Downloaded {downloaded} STAC item(s) to {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
