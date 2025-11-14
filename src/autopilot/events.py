"""Event publication utilities (RabbitMQ + CloudEvents-style payloads)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

try:
    import aio_pika  # type: ignore
    from aio_pika import Message  # type: ignore
except ImportError:  # pragma: no cover
    aio_pika = None  # type: ignore
    Message = None  # type: ignore

from .alerts import LoadedAlert
from .settings import get_settings


async def publish_alert_event(alert: LoadedAlert) -> dict[str, Any]:
    if aio_pika is None:  # pragma: no cover
        raise RuntimeError("aio_pika is required; install project dependencies before running")

    settings = get_settings()

    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(
            settings.alert_exchange,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

        event = {
            "specversion": "1.0",
            "id": alert.id,
            "type": f"alertzarr.alert.{alert.model.hazard_type}",
            "source": alert.model.source_url or "urn:alertzarr:alerts",
            "time": datetime.now(timezone.utc).isoformat(),
            "datacontenttype": "application/json",
            "data": alert.raw,
        }

        await exchange.publish(
            Message(body=json.dumps(event).encode("utf-8")),
            routing_key=settings.alert_routing_key,
        )
        return event
