# AlertZarr

AlertZarr ingests disaster alerts, looks up recent Sentinel-2 scenes over the AOI, writes a **placeholder** GeoZarr payload to MinIO, and emits a STAC Item + run report you can hand to downstream tooling. Run it locally or pull the container published to `ghcr.io/wietzesuijker/alertzarr`. The pipeline produces:

1. Normalised disaster alerts from sample feeds.
2. Simulated GeoZarr conversion artefacts.
3. Generated STAC Items that reference the produced data.
4. A run report capturing timing, status, and links for downstream consumers.

RabbitMQ, MinIO, and Postgres run via `docker-compose`, and the CLI (`alertzarr`) coordinates the alert-to-product flow. Configuration lives in `.env` (copy `.env.example`). GitHub Actions builds + pushes container images from `main` and tags, mirroring the `data-pipeline` release flow. The same execution steps map to hosted queues/object stores or Argo Workflows when deployed elsewhere.

## What the pipeline actually does

1. **Load & normalise the alert** (`autopilot.alerts`). AOI polygons and hazard metadata are validated via Pydantic.
2. **Publish a CloudEvents message** (`autopilot.events`) to RabbitMQ so other systems can react.
3. **Discover up to two recent Sentinel-2 scenes** (`autopilot.catalog`) intersecting the AOI (Earth-Search API, 7-day lookback, configurable cloud-cover threshold).
4. **Write a placeholder GeoZarr JSON** (`autopilot.geozarr`) into MinIO that captures the alert metadata plus any discovered scenes. This is a stand-in for a future real conversion step.
5. **Generate a STAC Item** (`autopilot.stac`) that references the GeoZarr artefact and links to the source scenes.
6. **Persist a run report** (`autopilot.reporting`) detailing timing, AOI size, and output URIs.

The GeoZarr artefact is intentionally minimal today; it demonstrates where downstream converters would slot in while keeping the pipeline runnable without massive workloads.

## Features
- Fetch & normalise sample Copernicus/GDACS alerts.
- Publish alerts to RabbitMQ as CloudEvents messages.
- Orchestrate a conversion workflow stub that writes a placeholder GeoZarr store to MinIO.
- Generate STAC Item JSON and upload it to MinIO alongside derived assets.
- Emit a run summary with timestamps and URLs.

## Repository Layout
```
.
├── README.md
├── docker-compose.yaml            # Local infrastructure (RabbitMQ, MinIO, Postgres, MinIO console)
├── Makefile                       # Convenience commands
├── pyproject.toml                 # Python project metadata (install via `uv` or `pip`)
├── data/
│   └── sample_alerts/             # Static alert payloads for quick runs
├── infra/
│   └── bootstrap_minio.py         # Seeds MinIO buckets and credentials for development
├── src/
│   └── autopilot/
│       ├── __init__.py
│       ├── alerts.py              # Alert ingestion + normalisation
│       ├── cli.py                 # Command-line entry point
│       ├── events.py              # RabbitMQ publishers/subscribers
│       ├── geozarr.py             # Placeholder GeoZarr conversion logic
│       ├── reporting.py           # Run summaries and logging helpers
│       └── stac.py                # STAC item generation
└── .github/workflows/             # CI + GHCR publishing pipeline
```

## Quickstart
1. **Install prerequisites**
   - Python 3.11+
   - [`uv`](https://github.com/astral-sh/uv) (or use `pip`) for dependency management
   - Docker / Docker Compose

2. **Install Python dependencies**
   ```bash
   uv sync
   ```

3. **Start local services**
   ```bash
   make up
   # waits until MinIO + RabbitMQ report healthy
   ```

4. **Seed MinIO (optional)**
   ```bash
   uv run python infra/bootstrap_minio.py
   ```

5. **Run the pipeline**
   ```bash
   uv run alertzarr \
       --alert copernicus_flood.json \
     --hazard flood
   ```
    The `--alert` flag is relative to `data/sample_alerts/`.
    Each invocation writes a run summary JSON under `local/run_reports/<run_id>.json` by default.
   Use `--report-dir /custom/path` to override the destination.

6. **Inspect results**
   - MinIO: http://localhost:9001 (default creds `autopilot/autopilot123`)
   - RabbitMQ: http://localhost:15672 (`guest/guest`)
   - STAC Item: see path logged in the run summary.
   - Run summaries: `local/run_reports/<run_id>.json` (or the directory passed via `--report-dir`).

## Run from GitHub Actions

Use the `Demo AlertZarr` workflow (`.github/workflows/demo.yml`) to execute the same steps on a GitHub-hosted runner. Trigger it via **Actions → Demo AlertZarr → Run workflow**, choose a sample alert, and download the uploaded `alertzarr-run-report` artifact for the resulting summary JSON.

## Next Steps
- Replace sample alerts with live API polling and webhook integrations.
- Swap the conversion stub with real `eopf-geozarr` workflows and Argo templates.
- Integrate Prometheus/Grafana dashboards for run observability.
- Package as reusable Helm charts/Kustomize overlays once production-ready.

7. **Run the unit tests**
   ```bash
   uv run pytest
   ```

8. **Build container locally (optional)**
   ```bash
   docker build -t alertzarr:local .
   docker run --rm alertzarr:local --help
   ```

## Publishing & GHCR Flow

- **Push to GitHub**: commits to `main` (or version tags like `v0.2.0`) trigger `.github/workflows/build.yml`. No extra secrets are required because the workflow uses `${{ secrets.GITHUB_TOKEN }}` to authenticate to GHCR.
- **CI stages**: lint (`ruff`), tests (`pytest`), then Docker build + push. Pull requests build but skip pushing the container image.
- **Image tags**: successful pushes publish `ghcr.io/wietzesuijker/alertzarr:${GITHUB_SHA}` and `ghcr.io/wietzesuijker/alertzarr:latest`.
- **Using the image**:
   ```bash
   docker pull ghcr.io/wietzesuijker/alertzarr:latest
   docker run --rm ghcr.io/wietzesuijker/alertzarr:latest --help
   ```

If you fork the repo, adjust the workflow tags/owner and ensure `packages: write` permissions stay enabled so your GitHub token can push to your GHCR namespace.

## Example run summary

The CLI persists a machine-readable report for every invocation. Example (truncated) output from `local/run_reports/584654539a3a45cc8eac07ce07ae14c2.json`:

```json
{
   "run_id": "584654539a3a45cc8eac07ce07ae14c2",
   "alert_id": "COP_EMS_2025_000123",
   "steps": {
      "alert": {
         "hazard": "flood",
         "severity": "Severe",
         "area_km2": 391.0
      },
      "conversion": {
         "s3_uri": "s3://autopilot-geozarr/alerts/flood/COP_EMS_2025_000123/geozarr-placeholder.json",
         "source_scene_ids": [
            "S2A_29SND_20251002_0_L2A",
            "S2C_29SND_20250930_0_L2A"
         ]
      },
      "stac_item": {
         "href": "s3://autopilot-stac/items/COP_EMS_2025_000123-geozarr.json"
      }
   }
}
```

Use these reports to feed dashboards, attach to Slack alerts, or trigger downstream conversions once the real GeoZarr step is wired up.

## Current scope & limitations

- The GeoZarr artefact is a JSON stub, not a full raster conversion. Swap `autopilot.geozarr.simulate_conversion` with a real converter when ready.
- Scene discovery hits Earth-Search and is best-effort. Network errors simply log a warning and continue.
- The pipeline targets the sample Copernicus alerts included in `data/sample_alerts/`. Bring your own alerts by dropping JSON files with the same schema.
- Titiler visualisation is not bundled yet; consume the generated STAC Item + GeoZarr metadata with your own viewers.
