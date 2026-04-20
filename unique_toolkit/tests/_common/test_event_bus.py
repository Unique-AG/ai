import asyncio

import pytest

from unique_toolkit._common.event_bus import TypedEventBus


@pytest.mark.asyncio
async def test_subscribe_and_publish_and_wait_async__sync_handler():
    bus = TypedEventBus[str]()
    received: list[str] = []

    def handler(event: str) -> None:
        received.append(event)

    bus.subscribe(handler)
    await bus.publish_and_wait_async("hello")

    assert received == ["hello"]


@pytest.mark.asyncio
async def test_subscribe_and_publish_and_wait_async__async_handler():
    bus = TypedEventBus[str]()
    received: list[str] = []

    async def handler(event: str) -> None:
        received.append(event)

    bus.subscribe(handler)
    await bus.publish_and_wait_async("world")

    assert received == ["world"]


@pytest.mark.asyncio
async def test_publish_and_wait_async__multiple_handlers():
    bus = TypedEventBus[int]()
    results: list[int] = []

    bus.subscribe(lambda e: results.append(e * 2))
    bus.subscribe(lambda e: results.append(e * 3))

    await bus.publish_and_wait_async(5)

    assert sorted(results) == [10, 15]


@pytest.mark.asyncio
async def test_publish_and_wait_async__no_handlers():
    bus = TypedEventBus[str]()
    await bus.publish_and_wait_async("nothing")


@pytest.mark.asyncio
async def test_publish_and_forget_async__fire_and_forget():
    bus = TypedEventBus[str]()
    received: list[str] = []

    async def handler(event: str) -> None:
        received.append(event)

    bus.subscribe(handler)
    tasks = bus.publish_and_forget_async("fire")
    await asyncio.gather(*tasks)

    assert received == ["fire"]


@pytest.mark.asyncio
async def test_cancel_subscription__removes_handler():
    bus = TypedEventBus[str]()
    received: list[str] = []

    sub = bus.subscribe(lambda e: received.append(e))
    await bus.publish_and_wait_async("before")
    assert received == ["before"]

    sub.cancel()
    await bus.publish_and_wait_async("after")
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


def test_publish_and_wait__sync_handler__no_loop():
    bus = TypedEventBus[str]()
    received: list[str] = []

    bus.subscribe(lambda e: received.append(e))
    bus.publish_and_wait("sync-no-loop")

    assert received == ["sync-no-loop"]


@pytest.mark.asyncio
async def test_publish_and_wait__sync_handler__with_loop():
    bus = TypedEventBus[str]()
    received: list[str] = []

    bus.subscribe(lambda e: received.append(e))
    bus.publish_and_wait("sync-with-loop")

    assert received == ["sync-with-loop"]


@pytest.mark.asyncio
async def test_publish_and_wait__async_handler__with_loop():
    bus = TypedEventBus[str]()
    received: list[str] = []

    async def handler(event: str) -> None:
        received.append(event)

    bus.subscribe(handler)
    bus.publish_and_wait("async-with-loop")
    await asyncio.sleep(0)

    assert received == ["async-with-loop"]


def test_publish_and_wait__async_handler__no_loop_skips(caplog):
    bus = TypedEventBus[str]()

    async def handler(event: str) -> None:
        pass

    bus.subscribe(handler)
    bus.publish_and_wait("no-loop")

    assert "Skipping async handler" in caplog.text


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_publish_and_wait_async__return_exceptions__isolates_flaky_subscribers(
    caplog,
):
    """
    Purpose: ``return_exceptions=True`` must let the non-flaky subscribers
      complete while the raising one is logged and swallowed.
    Why this matters: Hot-path publishes (e.g. TextDelta) must not be
      aborted by a single flaky analytics subscriber — otherwise one
      misbehaving add-on kills the whole stream.
    Setup summary: Two subscribers, one raises, one records; publish with
      ``return_exceptions=True`` and assert no exception propagates, the
      good subscriber still receives the event, and the failure is logged.
    """
    import logging

    bus = TypedEventBus[str]()
    received: list[str] = []

    async def raising(event: str) -> None:
        raise RuntimeError("boom")

    async def good(event: str) -> None:
        received.append(event)

    bus.subscribe(raising)
    bus.subscribe(good)

    with caplog.at_level(logging.ERROR, logger="unique_toolkit._common.event_bus"):
        await bus.publish_and_wait_async("hi", return_exceptions=True)

    assert received == ["hi"]
    assert any("raised during publish" in r.getMessage() for r in caplog.records)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_publish_and_wait_async__default__propagates_exception():
    """
    Purpose: Default ``return_exceptions=False`` must still propagate a
      raising subscriber's exception.
    Why this matters: Critical-path events (e.g. stream_started) rely on
      loud failures rather than silent drops.
    Setup summary: One raising subscriber on a bus; publish without
      ``return_exceptions`` and assert ``RuntimeError`` propagates.
    """
    bus = TypedEventBus[str]()

    async def raising(event: str) -> None:
        raise RuntimeError("boom")

    bus.subscribe(raising)

    with pytest.raises(RuntimeError, match="boom"):
        await bus.publish_and_wait_async("hi")
