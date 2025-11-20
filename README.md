# AlertZarr

AlertZarr converts disaster alerts into GeoZarr artefacts plus matching STAC items. The CLI takes an alert payload, looks up fresh Sentinel-2 scenes through the EODC STAC API, runs `eopf-geozarr` to build the GeoZarr store, and records the result inside a run report.

## Workflow
1. Validate the alert input (`autopilot.alerts`).
2. (Optional) emit a CloudEvents message via RabbitMQ (`autopilot.events`).
3. Discover recent Sentinel-2 L2A scenes intersecting the AOI (`autopilot.catalog`).
4. Convert the newest eligible Zarr v2 scene to GeoZarr or fall back to the placeholder (`autopilot.geozarr`).
5. Publish a STAC Item and persist a run report (`autopilot.stac`, `autopilot.reporting`).

Dependencies: Python 3.11+, `uv` for dependency management, and RabbitMQ + MinIO via `docker-compose`. Copy `.env.example` to `.env` to configure credentials.

## Repository layout
```
├── data/sample_alerts/        Sample alert payloads
├── infra/bootstrap_minio.py   Seeds local MinIO buckets
├── scripts/download_stac_items.py
├── src/autopilot/             CLI + pipeline modules
├── tests/                     Unit tests
└── docker-compose.yaml        RabbitMQ + MinIO services
```

## Run locally
```bash
uv sync                                  # install dependencies
make up                                  # start RabbitMQ + MinIO
uv run python infra/bootstrap_minio.py   # optional bucket bootstrap
uv run alertzarr --alert copernicus_flood.json --hazard flood
```

Outputs land under `local/run_reports/<run_id>.json` and in the MinIO buckets defined in `.env`. Use `--conversion-mode real|auto|simulate`, `--report-dir`, or `--no-scene-search` to adapt behaviour.

## Development shortcuts
- `uv run ruff check src`
- `uv run pytest`
- `make down`

## Automation
The `Demo AlertZarr` workflow (`.github/workflows/demo.yml`) runs the CLI on GitHub Actions, seeds RabbitMQ/MinIO, and uploads the run report plus generated STAC items. The default CI workflow (`.github/workflows/build.yml`) handles linting, tests, and publishing the container image to GHCR.

## Run report example
```json
{
  "run_id": "584654539a3a45cc8eac07ce07ae14c2",
  "alert_id": "COP_EMS_2025_000123",
  "steps": {
    "hazard": "flood",
    "conversion": {
      "s3_uri": "s3://autopilot-geozarr/alerts/flood/COP_EMS_2025_000123/geozarr-placeholder.json"
    }
  }
}
```

Refer to `local/run_reports` for the latest outputs or downstream automation hooks.

## Scope hints
- Conversion currently targets Sentinel-2 L2A Zarr v2 scenes exposed via the EODC catalog. If no scene intersects the AOI, the pipeline falls back to the JSON placeholder so STAC + reporting still succeed.
- TiTiler links are emitted only when `TITILER_BASE_URL` is configured.
- Add your own alerts by dropping JSON files that match the sample schema into `data/sample_alerts/`.
