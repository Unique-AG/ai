import asyncio

import pytest

from unique_toolkit._common.event_bus import TypedEventBus


@pytest.mark.asyncio
async def test_subscribe_and_publish_and_wait__sync_handler():
    bus = TypedEventBus[str]()
    received: list[str] = []

    def handler(event: str) -> None:
        received.append(event)

    bus.subscribe(handler)
    await bus.publish_and_wait("hello")

    assert received == ["hello"]


@pytest.mark.asyncio
async def test_subscribe_and_publish_and_wait__async_handler():
    bus = TypedEventBus[str]()
    received: list[str] = []

    async def handler(event: str) -> None:
        received.append(event)

    bus.subscribe(handler)
    await bus.publish_and_wait("world")

    assert received == ["world"]


@pytest.mark.asyncio
async def test_publish_and_wait__multiple_handlers():
    bus = TypedEventBus[int]()
    results: list[int] = []

    bus.subscribe(lambda e: results.append(e * 2))
    bus.subscribe(lambda e: results.append(e * 3))

    await bus.publish_and_wait(5)

    assert sorted(results) == [10, 15]


@pytest.mark.asyncio
async def test_publish_and_wait__no_handlers():
    bus = TypedEventBus[str]()
    await bus.publish_and_wait("nothing")


@pytest.mark.asyncio
async def test_publish__fire_and_forget():
    bus = TypedEventBus[str]()
    received: list[str] = []

    async def handler(event: str) -> None:
        received.append(event)

    bus.subscribe(handler)
    tasks = bus.publish("fire")
    await asyncio.gather(*tasks)

    assert received == ["fire"]


@pytest.mark.asyncio
async def test_cancel_subscription__removes_handler():
    bus = TypedEventBus[str]()
    received: list[str] = []

    sub = bus.subscribe(lambda e: received.append(e))
    await bus.publish_and_wait("before")
    assert received == ["before"]

    sub.cancel()
    await bus.publish_and_wait("after")
    assert received == ["before"]


@pytest.mark.asyncio
async def test_cancel_subscription__idempotent():
    bus = TypedEventBus[str]()
    sub = bus.subscribe(lambda e: None)
    sub.cancel()
    sub.cancel()


@pytest.mark.asyncio
async def test_cancel_subscription__already_removed():
    bus = TypedEventBus[str]()
    handler = lambda e: None  # noqa: E731
    sub = bus.subscribe(handler)
    bus._handlers.clear()
    sub.cancel()
