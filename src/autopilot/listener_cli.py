"""Command-line entry point for the alert listener service."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from .events import publish_alert_event
from .listener import AlertFeedClient, AlertFeedSpec, AlertListener
from .logging_utils import configure_logging
from .settings import get_settings
from .state import AlertStateStore


@click.command()
@click.option("--once", is_flag=True, help="Run a single polling cycle then exit.")
def main(once: bool) -> None:
    """Bootstrap the alert ingestion pipeline."""
    configure_logging()
    settings = get_settings()
    if not settings.alert_feed_specs:
        raise SystemExit("Configure ALERT_FEED_SPECS before running the listener")

    feed_specs = [
        AlertFeedSpec.parse(spec, index)
        for index, spec in enumerate(settings.alert_feed_specs, start=1)
    ]
    feeds = [AlertFeedClient(spec) for spec in feed_specs]
    state_store = AlertStateStore(Path(settings.alert_listener_state_path))
    listener = AlertListener(
        feeds,
        publish_alert_event,
        state_store,
        poll_seconds=settings.alert_listener_poll_seconds,
    )

    async def runner() -> None:
        if once:
            await listener.run_once()
        else:
            await listener.run_forever()

    asyncio.run(runner())


if __name__ == "__main__":  # pragma: no cover
    main()
