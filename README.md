# AlertZarr

AlertZarr turns disaster alerts into ready-to-serve GeoZarr and STAC artefacts using lightweight local services. Run it locally or as a container built automatically via GitHub Actions + GHCR under `ghcr.io/wietzesuijker/alertzarr`. The pipeline produces:

1. Normalised disaster alerts from sample feeds.
2. Simulated GeoZarr conversion artefacts.
3. Generated STAC Items that reference the produced data.
4. A run report capturing timing, status, and links for downstream consumers.

The stack stays deliberately compact: RabbitMQ, MinIO, and Postgres run via `docker-compose`, while the Python pipeline coordinates the alert-to-product flow. Environment variables live in `.env` (copy `.env.example`), and the included CLI (`alertzarr`) keeps execution repeatable. GitHub Actions mirrors `data-pipeline`'s build-to-GHCR approach so `main` and tagged releases automatically publish container images. When it is time to scale, the same concepts port to Argo Workflows, managed object stores, and live alert feeds.

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

6. **Inspect results**
   - MinIO: http://localhost:9001 (default creds `autopilot/autopilot123`)
   - RabbitMQ: http://localhost:15672 (`guest/guest`)
   - STAC Item: see path logged in the run summary.

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

AlertZarr is intentionally lean yet functional—ideal for piloting with stakeholders before hardening into production infrastructure or deploying from `wietzesuijker/alertzarr` straight to GHCR.
