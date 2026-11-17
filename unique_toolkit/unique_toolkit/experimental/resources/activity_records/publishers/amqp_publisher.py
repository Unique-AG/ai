"""AMQP publisher for activity records. This module is the only one that imports aio-pika."""

from __future__ import annotations

import asyncio
import logging
import socket
from collections.abc import Sequence
from typing import Final
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

from unique_toolkit.experimental.resources.activity_records.config import AmqpSettings
from unique_toolkit.experimental.resources.activity_records.json_size import json_bytes
from unique_toolkit.experimental.resources.activity_records.prepare import WireEvent

try:
    import aio_pika  # pyright: ignore[reportMissingImports]
    from aio_pika import DeliveryMode, Message  # pyright: ignore[reportMissingImports]
    from aio_pika.abc import (  # pyright: ignore[reportMissingImports]
        AbstractExchange,
        AbstractRobustConnection,
    )
    from aio_pika.connection import make_url  # pyright: ignore[reportMissingImports]
    from aio_pika.robust_channel import (  # pyright: ignore[reportMissingImports]
        RobustChannel,
    )
except ImportError as error:  # pragma: no cover
    raise ImportError(
        "The AMQP publisher needs aio-pika. "
        "Install it with: uv add 'unique-toolkit[activity-records-amqp]'"
    ) from error

ROUTING_KEY: Final = "unique.activity-records.ingest"
CONTENT_TYPE: Final = "application/cloudevents-batch+json"
logger = logging.getLogger(__name__)


def _connection_url(settings: AmqpSettings) -> str:
    parts = urlsplit(settings.connection_url)
    query = {
        "heartbeat": str(settings.heartbeat_interval_in_seconds),
        "name": f"{socket.gethostname()}-activity-records:publisher",
        **dict(parse_qsl(parts.query)),
    }
    return urlunsplit(parts._replace(query=urlencode(query, safe=":")))


class AmqpPublisher:
    """Publishes each batch to the ingest queue as one persistent message. The caller owns it:
    ``connect()`` before the outbox starts, ``close()`` after it stops."""

    def __init__(self, exchange: str = "") -> None:
        self._exchange_name = exchange
        self._connection: AbstractRobustConnection | None = None
        self._channel: RobustChannel | None = None
        self._connect_task: asyncio.Task[None] | None = None

    async def connect(self) -> None:
        """Start connecting in the background and return at once. Raises ``ValidationError``
        when no broker is configured."""
        if self._connection is not None:
            return
        settings = AmqpSettings()
        connection = aio_pika.RobustConnection(
            make_url(_connection_url(settings)),
            fail_fast=False,
        )
        self._connection = connection

        async def connect_in_background() -> None:
            try:
                await connection.connect()
            except Exception as error:
                logger.warning(
                    "Activity Records broker connection failed (%s)",
                    type(error).__name__,
                )

        self._connect_task = asyncio.create_task(connect_in_background())

    async def close(self) -> None:
        """Cancel the connect task and close the connection. Safe to call twice."""
        task = self._connect_task
        self._connect_task = None
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        connection = self._connection
        self._connection = None
        self._channel = None
        if connection is not None:
            await connection.close()

    async def publish(self, events: Sequence[WireEvent]) -> None:
        """Raises ``RuntimeError`` before ``connect()``, aio-pika's ``PublishError`` for an
        unroutable message and ``DeliveryError`` for a nack."""
        exchange = await self._exchange()
        await exchange.publish(
            Message(
                json_bytes(events),
                content_type=CONTENT_TYPE,
                delivery_mode=DeliveryMode.PERSISTENT,
                message_id=str(uuid4()),
            ),
            routing_key=ROUTING_KEY,
            mandatory=True,
        )

    async def _exchange(self) -> AbstractExchange:
        channel = await self._open_channel()
        if self._exchange_name == "":
            return channel.default_exchange
        # ensure=False does not declare and does not passive-declare.
        return await channel.get_exchange(self._exchange_name, ensure=False)

    async def _open_channel(self) -> RobustChannel:
        connection = self._connection
        if connection is None:
            raise RuntimeError("Activity records publisher is not connected")
        await connection.ready()
        channel = self._channel
        if channel is None:
            # A robust channel reopens itself after a reconnect, so it is opened once.
            # aio-pika 9: on_return_raises maps a mandatory return to PublishError and a nack to DeliveryError.
            opened = await connection.channel(
                publisher_confirms=True, on_return_raises=True
            )
            assert isinstance(opened, RobustChannel)
            channel = self._channel = opened
        await channel.ready()
        return channel
