"""AmqpPublisher: settings and lifecycle without a broker, delivery against a RabbitMQ container."""

from __future__ import annotations

import asyncio
import json
import socket
import subprocess
import time
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import pytest
from pydantic import ValidationError

aio_pika = pytest.importorskip(
    "aio_pika",
    reason="Activity Records publisher tests need the activity-records-amqp extra",
)

from unique_toolkit.experimental.resources.activity_records.config import (  # noqa: E402
    AmqpSettings,
)
from unique_toolkit.experimental.resources.activity_records.publishers.amqp_publisher import (  # noqa: E402
    CONTENT_TYPE,
    ROUTING_KEY,
    AmqpPublisher,
    _connection_url,
)

from .conftest import wait_until  # noqa: E402

pytestmark = pytest.mark.ai

_AMQP_ENV = (
    "AMQP_URL",
    "AMQP_HOST",
    "AMQP_PORT",
    "AMQP_USERNAME",
    "AMQP_PASSWORD",
    "AMQP_VHOST",
    "AMQP_HEARTBEAT_INTERVAL_IN_SECONDS",
)
_CONNECTION_NAME = f"{socket.gethostname()}-activity-records:publisher"


@pytest.fixture
def amqp_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in _AMQP_ENV:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def _query(url: str) -> dict[str, str]:
    return dict(parse_qsl(urlsplit(url).query))


def test_connection_url_encodes_credentials_and_adds_heartbeat_and_name(
    amqp_env: pytest.MonkeyPatch,
) -> None:
    amqp_env.setenv("AMQP_HOST", "broker")
    amqp_env.setenv("AMQP_USERNAME", "us er")
    amqp_env.setenv("AMQP_PASSWORD", "p@ss/word")
    amqp_env.setenv("AMQP_VHOST", "/a b")

    url = _connection_url(AmqpSettings())

    assert url.startswith("amqp://us%20er:p%40ss%2Fword@broker:5672/%2Fa%20b?")
    assert _query(url) == {"heartbeat": "30", "name": _CONNECTION_NAME}


def test_an_explicit_url_keeps_its_own_query(amqp_env: pytest.MonkeyPatch) -> None:
    amqp_env.setenv("AMQP_URL", "amqp://broker/?heartbeat=5&custom=value")

    assert _query(_connection_url(AmqpSettings())) == {
        "heartbeat": "5",
        "custom": "value",
        "name": _CONNECTION_NAME,
    }


@pytest.mark.parametrize(
    ("env", "valid"),
    [
        ({}, False),
        ({"AMQP_URL": ""}, False),
        ({"AMQP_HOST": "broker"}, False),
        ({"AMQP_HOST": "broker", "AMQP_USERNAME": "user"}, False),
        ({"AMQP_URL": "amqp://broker"}, True),
        (
            {
                "AMQP_HOST": "broker",
                "AMQP_USERNAME": "user",
                "AMQP_PASSWORD": "secret",
            },
            True,
        ),
    ],
)
def test_settings_need_a_url_or_host_with_credentials(
    amqp_env: pytest.MonkeyPatch, env: dict[str, str], valid: bool
) -> None:
    for name, value in env.items():
        amqp_env.setenv(name, value)

    if valid:
        AmqpSettings()
    else:
        with pytest.raises(ValidationError):
            AmqpSettings()


async def test_publish_before_connect_raises() -> None:
    with pytest.raises(RuntimeError):
        await AmqpPublisher().publish([{"id": "event"}])


async def test_close_without_connect_is_a_no_op() -> None:
    publisher = AmqpPublisher()
    await publisher.close()
    await publisher.close()


async def test_connect_does_not_block_while_the_broker_is_down(
    amqp_env: pytest.MonkeyPatch,
) -> None:
    amqp_env.setenv("AMQP_URL", "amqp://127.0.0.1:1/")
    publisher = AmqpPublisher()

    await asyncio.wait_for(publisher.connect(), 1)
    await publisher.connect()
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(publisher.publish([{"id": "event"}]), 0.5)
    await asyncio.wait_for(publisher.close(), 5)


def _restart_broker(container: str) -> None:
    for action in ("stop_app", "start_app"):
        subprocess.run(
            ["docker", "exec", container, "rabbitmqctl", action],
            check=True,
            capture_output=True,
        )


@pytest.fixture
def amqp(monkeypatch: pytest.MonkeyPatch, rabbitmq: tuple[str, str]) -> tuple[str, str]:
    url, container = rabbitmq
    monkeypatch.setenv("AMQP_URL", url)
    return url, container


async def _declare_queue(
    url: str, name: str, *, purge: bool = True
) -> tuple[aio_pika.abc.AbstractConnection, aio_pika.abc.AbstractQueue]:
    connection = await aio_pika.connect(url)
    channel = await connection.channel()
    queue = await channel.declare_queue(
        name, durable=True, exclusive=False, auto_delete=False
    )
    if purge:
        await queue.purge()
    return connection, queue


async def _take(
    queue: aio_pika.abc.AbstractQueue, event_id: str
) -> aio_pika.abc.AbstractIncomingMessage:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        incoming = await queue.get(timeout=1, fail=False, no_ack=True)
        if incoming is not None and json.loads(incoming.body) == [{"id": event_id}]:
            return incoming
    raise AssertionError(f"message {event_id} was not delivered")


async def _publish_until_it_succeeds(
    publisher: AmqpPublisher, event_id: str, seconds: float = 40
) -> None:
    deadline = time.monotonic() + seconds
    while True:
        try:
            await asyncio.wait_for(publisher.publish([{"id": event_id}]), 5)
            return
        except Exception:
            if time.monotonic() > deadline:
                raise
            await asyncio.sleep(1)


def _assert_message(
    incoming: aio_pika.abc.AbstractIncomingMessage, payload: list[dict[str, Any]]
) -> None:
    assert json.loads(incoming.body) == payload
    assert incoming.content_type == CONTENT_TYPE
    assert incoming.delivery_mode == aio_pika.DeliveryMode.PERSISTENT
    assert incoming.message_id
    assert not incoming.headers


async def test_publish_confirms_persistent_batch_with_distinct_ids(
    amqp: tuple[str, str],
) -> None:
    url, _container = amqp
    connection, queue = await _declare_queue(url, ROUTING_KEY)
    publisher = AmqpPublisher()
    payload = [{"id": "1", "note": "café"}]
    await publisher.connect()
    try:
        await publisher.publish(payload)
        await publisher.publish(payload)
        first = await queue.get(timeout=5, no_ack=True)
        second = await queue.get(timeout=5, no_ack=True)
    finally:
        await publisher.close()
        await connection.close()
    _assert_message(first, payload)
    _assert_message(second, payload)
    assert first.message_id != second.message_id


async def test_publish_to_a_dedicated_exchange(amqp: tuple[str, str]) -> None:
    url, _container = amqp
    connection = await aio_pika.connect(url)
    channel = await connection.channel()
    exchange = await channel.declare_exchange(
        "activity-records-test", aio_pika.ExchangeType.DIRECT
    )
    queue = await channel.declare_queue("", exclusive=True, auto_delete=True)
    await queue.bind(exchange, routing_key=ROUTING_KEY)
    publisher = AmqpPublisher(exchange="activity-records-test")
    payload = [{"id": "dedicated"}]
    await publisher.connect()
    try:
        await publisher.publish(payload)
        incoming = await queue.get(timeout=5, no_ack=True)
    finally:
        await publisher.close()
        await connection.close()
    _assert_message(incoming, payload)


async def test_unroutable_publish_is_rejected(amqp: tuple[str, str]) -> None:
    url, _container = amqp
    connection = await aio_pika.connect(url)
    channel = await connection.channel()
    await channel.declare_exchange(
        "activity-records-unroutable", aio_pika.ExchangeType.DIRECT
    )
    publisher = AmqpPublisher(exchange="activity-records-unroutable")
    await publisher.connect()
    try:
        with pytest.raises(aio_pika.exceptions.PublishError) as caught:
            await publisher.publish([{"secret": "payload-secret-do-not-log"}])
    finally:
        await publisher.close()
        await connection.close()
    assert "payload-secret-do-not-log" not in str(caught.value)


async def test_the_same_publisher_recovers_after_a_paused_broker(
    amqp: tuple[str, str],
) -> None:
    url, container = amqp
    connection, queue = await _declare_queue(url, ROUTING_KEY)
    publisher = AmqpPublisher()
    await publisher.connect()
    try:
        await publisher.publish([{"id": "warm-up"}])
        await _take(queue, "warm-up")
        subprocess.run(["docker", "pause", container], check=True)
        try:
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(publisher.publish([{"id": "blocked"}]), 1)
        finally:
            subprocess.run(["docker", "unpause", container], check=True)
        await _publish_until_it_succeeds(publisher, "recovered")
        await asyncio.wait_for(publisher.publish([{"id": "plain"}]), 5)
        await _take(queue, "plain")
        incoming = await _take(queue, "recovered")
    finally:
        subprocess.run(["docker", "unpause", container], capture_output=True)
        await publisher.close()
        await connection.close()
    assert json.loads(incoming.body) == [{"id": "recovered"}]


async def test_publish_succeeds_after_broker_restart(amqp: tuple[str, str]) -> None:
    url, container = amqp
    connection, queue = await _declare_queue(url, ROUTING_KEY)
    publisher = AmqpPublisher()
    await publisher.connect()
    try:
        await publisher.publish([{"id": "before-restart"}])
        await _take(queue, "before-restart")
        _restart_broker(container)
        await wait_until(lambda: aio_pika.connect(url), 90)
        await connection.close()
        await _publish_until_it_succeeds(publisher, "after-restart")
        await asyncio.wait_for(publisher.publish([{"id": "plain"}]), 5)
        connection, queue = await _declare_queue(url, ROUTING_KEY, purge=False)
        await _take(queue, "plain")
        incoming = await _take(queue, "after-restart")
    finally:
        await publisher.close()
        await connection.close()
    assert json.loads(incoming.body) == [{"id": "after-restart"}]
