# AlertZarr

AlertZarr turns disaster alerts into ready-to-serve GeoZarr and STAC artefacts using RabbitMQ, MinIO, and a Python CLI. Run it locally or pull the container published to `ghcr.io/wietzesuijker/alertzarr`. The pipeline produces:

1. Normalised disaster alerts from sample feeds.
2. Simulated GeoZarr conversion artefacts.
3. Generated STAC Items that reference the produced data.
4. A run report capturing timing, status, and links for downstream consumers.

RabbitMQ, MinIO, and Postgres run via `docker-compose`, and the CLI (`alertzarr`) coordinates the alert-to-product flow. Configuration lives in `.env` (copy `.env.example`). GitHub Actions builds + pushes container images from `main` and tags, mirroring the `data-pipeline` release flow. The same execution steps map to hosted queues/object stores or Argo Workflows when deployed elsewhere.

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
     --alert sample_alerts/copernicus_flood.json \
     --hazard flood
   ```
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
