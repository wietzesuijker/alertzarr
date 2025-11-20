"""CLI entry point for the alert-to-product pipeline."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .alerts import load_alert
from .events import publish_alert_event
from .geozarr import ConversionMode, convert_alert
from .logging_utils import configure_logging
from .reporting import RunReporter
from .settings import get_settings
from .stac import create_stac_item

configure_logging()
LOGGER = logging.getLogger(__name__)
CONSOLE = Console()


async def orchestrate(
    alert_path: Path,
    hazard: str,
    run_id: str | None = None,
    no_scene_search: bool = False,
    report_dir: Path | None = None,
    conversion_mode: ConversionMode = "auto",
) -> None:
    settings = get_settings()
    reporter = RunReporter(run_id=run_id)
    reporter.start_run()

    alert = load_alert(alert_path)
    reporter.record_alert(alert)
    CONSOLE.print(
        f"Loaded alert [bold]{alert.id}[/bold] for hazard [green]{hazard}[/green]"
    )

    await publish_alert_event(alert)
    reporter.record_event_publish()
    CONSOLE.print("Published alert to RabbitMQ")

    report_path: Path | None = None
    try:
        geozarr_output = await convert_alert(
            alert,
            include_scene_search=not no_scene_search,
            mode=conversion_mode,
        )
        reporter.record_conversion(geozarr_output)
        artifact = (
            "GeoZarr" if geozarr_output.key.endswith(".zarr") else "placeholder JSON"
        )
        CONSOLE.print(f"Wrote {artifact} artefact to {geozarr_output.s3_uri}")
        scene_count = len(geozarr_output.scenes)
        if scene_count:
            scene_ids = ", ".join(scene.id for scene in geozarr_output.scenes)
            CONSOLE.print(
                f"Found {scene_count} Sentinel scene(s) intersecting the AOI: {scene_ids}"
            )
        else:
            CONSOLE.print("No Sentinel-2 scenes matched the EODC search criteria")

        stac_item = await create_stac_item(alert, geozarr_output)
        reporter.record_stac_item(stac_item)
        CONSOLE.print(f"Created STAC Item: {stac_item['id']}")
    except RuntimeError as exc:
        reporter.status = "failed"
        raise SystemExit(str(exc)) from exc
    finally:
        reporter.finish_run()
        reporter.emit_metrics(Path(settings.metrics_path))
        if report_dir is not None:
            report_path = reporter.persist(report_dir)

    CONSOLE.print("[bold green]Pipeline completed successfully[/bold green]")

    table = Table(title="Run Summary")
    table.add_column("Step")
    table.add_column("Value")

    for key, value in reporter.summary().items():
        if isinstance(value, (dict, list)):
            rendered = json.dumps(value, indent=2)
        else:
            rendered = str(value)
        table.add_row(key, rendered)

    CONSOLE.print(table)
    if report_path is not None:
        CONSOLE.print(f"Saved run summary to [cyan]{report_path}[/cyan]")


@click.command()
@click.option(
    "--alert",
    "alert_relative",
    type=str,
    required=True,
    help="Relative path under data/sample_alerts/",
)
@click.option(
    "--hazard", type=str, required=True, help="Hazard type (flood, wildfire, etc.)"
)
@click.option("--run-id", type=str, default=None, help="Optional run id override")
@click.option(
    "--no-scene-search",
    is_flag=True,
    default=False,
    help="Disable searching for overlapping Sentinel scenes",
)
@click.option(
    "--project-root",
    type=click.Path(path_type=Path),
    default=Path(__file__).resolve().parents[2],
    help="Project root path",
)
@click.option(
    "--report-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Directory for persisted run summaries (defaults to local/run_reports)",
)
@click.option(
    "--conversion-mode",
    type=click.Choice(["auto", "real", "simulate"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="auto uses real conversion when enabled, otherwise simulate",
)
def main(
    alert_relative: str,
    hazard: str,
    run_id: str | None,
    project_root: Path,
    no_scene_search: bool,
    report_dir: Path | None,
    conversion_mode: ConversionMode,
) -> None:
    data_root = project_root / "data" / "sample_alerts"
    alert_path = data_root / alert_relative
    if not alert_path.exists():
        raise SystemExit(f"Alert file not found: {alert_path}")

    default_report_dir = project_root / "local" / "run_reports"
    target_report_dir = report_dir or default_report_dir

    asyncio.run(
        orchestrate(
            alert_path,
            hazard,
            run_id,
            no_scene_search=no_scene_search,
            report_dir=target_report_dir,
            conversion_mode=conversion_mode,
        )
    )


if __name__ == "__main__":  # pragma: no cover
    main()
