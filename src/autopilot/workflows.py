"""Workflow orchestration utilities for AlertZarr."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

try:
    import aio_pika  # type: ignore
except ImportError:  # pragma: no cover
    aio_pika = None  # type: ignore

from .alerts import LoadedAlert, parse_alert_payload
from .settings import get_settings
from .state import AlertStateStore

LOGGER = logging.getLogger(__name__)


class WorkflowTrigger:
    """Submit parameterised Argo Workflows based on incoming alerts."""

    def __init__(
        self,
        base_url: str,
        namespace: str,
        template: str,
        token: str | None,
        timeout_seconds: float,
    ) -> None:
        if not base_url:
            raise ValueError("base_url must be provided for WorkflowTrigger")
        self.base_url = base_url.rstrip("/")
        self.namespace = namespace
        self.template = template
        self.token = token
        self.timeout_seconds = timeout_seconds

    async def submit(self, alert: LoadedAlert) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        payload = {
            "metadata": {
                "generateName": f"{self.template}-",
                "labels": {
                    "alertzarr.io/alert": alert.id,
                    "alertzarr.io/hazard": alert.model.hazard_type,
                },
            },
            "spec": {
                "workflowTemplateRef": {"name": self.template},
                "arguments": {
                    "parameters": [
                        {"name": "alert_id", "value": alert.id},
                        {"name": "hazard", "value": alert.model.hazard_type},
                        {"name": "severity", "value": alert.model.severity},
                        {
                            "name": "alert_payload",
                            "value": json.dumps(alert.raw, ensure_ascii=False),
                        },
                    ]
                },
            },
        }
        url = f"{self.base_url}/api/v1/workflows/{self.namespace}"
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds, headers=headers
        ) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()


class AlertEventSubscriber:
    """Subscribe to RabbitMQ alerts and trigger workflows."""

    def __init__(
        self,
        state_store: AlertStateStore,
        trigger: WorkflowTrigger,
        queue_name: str = "alertzarr.workflow",
    ) -> None:
        if aio_pika is None:  # pragma: no cover
            raise RuntimeError("aio_pika is required to run the subscriber")
        self.state_store = state_store
        self.trigger = trigger
        self.queue_name = queue_name

    async def run(self) -> None:
        settings = get_settings()
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue(self.queue_name, durable=True)
            await queue.bind(
                settings.alert_exchange, routing_key=settings.alert_routing_key
            )
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process(requeue=False):
                        await self._handle_message(message.body)

    async def _handle_message(self, body: bytes) -> None:
        try:
            event = json.loads(body)
            payload = event.get("data") or {}
            alert = parse_alert_payload(payload)
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("Discarding malformed message: %s", exc)
            return

        if not self.state_store.is_new(alert.id):
            LOGGER.debug(
                "Alert %s already processed; skipping workflow submission", alert.id
            )
            return

        try:
            await self.trigger.submit(alert)
        except Exception as exc:  # pragma: no cover
            LOGGER.exception("Workflow submission failed for %s: %s", alert.id, exc)
            raise
        else:
            self.state_store.mark_processed(alert.id)
            LOGGER.info("Submitted workflow for alert %s", alert.id)
