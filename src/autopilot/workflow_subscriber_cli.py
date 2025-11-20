"""Command-line entry point for the workflow subscriber."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from .logging_utils import configure_logging
from .settings import get_settings
from .state import AlertStateStore
from .workflows import AlertEventSubscriber, WorkflowTrigger


@click.command()
def main() -> None:
    """Launch the RabbitMQ subscriber that triggers Argo workflows."""
    configure_logging()
    settings = get_settings()
    if not settings.argo_base_url:
        raise SystemExit("Configure ARGO_BASE_URL to run the workflow subscriber")

    trigger = WorkflowTrigger(
        base_url=settings.argo_base_url,
        namespace=settings.argo_namespace,
        template=settings.argo_workflow_template,
        token=settings.argo_service_account_token,
        timeout_seconds=settings.workflow_submit_timeout_seconds,
    )
    state_store = AlertStateStore(Path(settings.workflow_trigger_state_path))
    subscriber = AlertEventSubscriber(state_store, trigger)

    asyncio.run(subscriber.run())


if __name__ == "__main__":  # pragma: no cover
    main()
