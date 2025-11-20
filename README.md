# AlertZarr

GeoZarr Disaster Response Auto-Pilot needs every alert to produce a GeoZarr data product, a STAC item, and a TiTiler viewer without manual patchwork. AlertZarr is the reference implementation: it ingests disaster alerts, runs GeoZarr conversions, registers assets, and now ships the automation scaffolding (always-on TiTiler links, alert listener, workflow subscriber, and metrics) required by the plan in `../cng-contracting/geozarr-disaster-response-autopilot-plan.md`.

## Why this matters
- **Alert-to-product automation:** Alert listener + workflow subscriber turn Copernicus/GDACS feeds into RabbitMQ events and Argo workflow submissions within minutes.
- **“Always live” access:** `TITILER_BASE_URL` and `STAC_PUBLIC_BASE_URL` are mandatory, so every run publishes viewer + TileJSON links ready for dashboards.
- **Operational awareness:** Each run emits structured metrics (`local/metrics.jsonl`) and richer run reports for Prometheus/Grafana ingestion and auditing.
- **Reusable modules:** Components line up with the plan’s architecture (listener layer, orchestration layer, processing layer, publishing layer, observability layer) and remain deployable via Docker Compose or GitHub Actions.

## Key components
| Layer | Module(s) | Purpose |
| --- | --- | --- |
| Alert listener | `autopilot.listener`, `autopilot.listener_cli` | Poll multiple feeds (`ALERT_FEED_SPECS`), normalise payloads, de-dupe via `AlertStateStore`, and publish CloudEvents to RabbitMQ. |
| Orchestration trigger | `autopilot.workflows`, `autopilot.workflow_subscriber_cli` | Consume RabbitMQ events, enforce once-per-alert workflows, and submit Argo templates with hazard-specific parameters. |
| Conversion & publishing | `autopilot.geozarr`, `autopilot.stac`, `autopilot.catalog` | Search EODC, write GeoZarr to MinIO/S3, build STAC with public links + TiTiler viewer/tilejson/info assets. |
| Observability | `autopilot.reporting`, `local/metrics.jsonl` | Persist JSON run summaries and append JSONL metrics (status, latency, data volume) for ingestion. |
| Tooling | `alertzarr`, `alertzarr-listener`, `alertzarr-workflow-subscriber` CLIs | Drive one-off runs, long-running listeners, and subscribers. |

## Documentation map
- [`alertzarr-docs/pipeline.md`](../alertzarr-docs/pipeline.md): End-to-end pipeline & infrastructure expectations.
- [`alertzarr-docs/operations.md`](../alertzarr-docs/operations.md): Operating procedures, bootstrap scripts, and dashboards.
- [`alertzarr-docs/limitations.md`](../alertzarr-docs/limitations.md): Known gaps + mitigation plans.
- [`alertzarr-docs/geozarr-preview.md`](../alertzarr-docs/geozarr-preview.md) & [`alertzarr-docs/value.md`](../alertzarr-docs/value.md): Preview/checkpoint strategy and product value messaging.

## Run locally
```bash
cp .env.example .env                      # ensure TiTiler/STAC URLs are set
uv sync                                   # install dependencies
make up                                   # rabbitmq, postgres, minio, titiler
uv run python infra/bootstrap_minio.py    # seed buckets (geo/stac)
uv run alertzarr --alert copernicus_flood.json --hazard flood

# optional automation services
uv run alertzarr-listener --once          # poll configured feeds once
uv run alertzarr-workflow-subscriber      # submit Argo workflows per alert
```

Outputs land under `local/run_reports/<run_id>.json`, viewer links reference `TITILER_BASE_URL`, STAC Items include public HTTP links, and JSONL metrics append to `local/metrics.jsonl` for scraping.

## GitHub automation
- `.github/workflows/build.yml`: lint, pytest, container build.
- `.github/workflows/demo.yml`: end-to-end run with RabbitMQ, MinIO, TiTiler, and artifact uploads. TiTiler is mandatory; runs fail fast if the viewer base URL or STAC public base URL is absent.

## Production readiness snapshot
| Capability | Status | Next steps |
| --- | --- | --- |
| Alert ingestion | ✅ Listener polls configured feeds, normalises payloads, persists last-seen IDs. | Expand feed coverage (national alerts), wire to Postgres for richer history + analytics. |
| Workflow orchestration | ✅ RabbitMQ subscriber submits Argo templates with dedupe guards. | Add hazard-specific DAG parameters, retries/circuit breakers, and deployment manifests (Terraform/Kustomize). |
| GeoZarr + publishing | ✅ GeoZarr writes enforced, STAC + TiTiler links emitted on every run. | Enable Sentinel-1 + hazard processors (NDWI/NBR), add validation against JSON Schemas. |
| Observability | ✅ JSON run reports + metrics JSONL. | Export structured Prometheus metrics, publish Grafana dashboards, integrate alerting. |
| User experience | 🚧 README + docs now explain the “why”, preview/value, and operations. | Land dashboard UI + notification channels (email/Slack) per plan. |

## Repository layout
```
├── data/sample_alerts/        Sample alert payloads
├── infra/bootstrap_minio.py   Seeds local MinIO buckets
├── scripts/download_stac_items.py
├── src/autopilot/             CLI + listener + workflow modules
├── tests/                     Unit tests
└── docker-compose.yaml        RabbitMQ + Postgres + MinIO + TiTiler
```

## Development shortcuts
- `uv run ruff check src`
- `uv run pytest`
- `make up` / `make down` / `make listener` / `make subscriber`

## Run report example
```json
{
  "run_id": "584654539a3a45cc8eac07ce07ae14c2",
  "alert_id": "COP_EMS_2025_000123",
  "status": "succeeded",
  "steps": {
    "alert": {
      "hazard": "flood"
    },
    "conversion": {
      "s3_uri": "s3://autopilot-geozarr/alerts/flood/COP_EMS_2025_000123/geozarr-placeholder.json",
      "viewer": {
        "viewer_url": "http://localhost:8080/collections/flood/items/COP_EMS_2025_000123/viewer"
      }
    }
  }
}
```

Every run also emits a metrics line similar to:

```json
{"timestamp":"2025-05-05T09:42:11Z","run_id":"5846545...","alert_id":"COP_EMS_2025_000123","status":"succeeded","duration_seconds":187.4,"bytes_written":42800123,"source_scene_count":1}
```

Use these files for dashboards, post-run QA, or to feed the broader Auto-Pilot pipeline.
