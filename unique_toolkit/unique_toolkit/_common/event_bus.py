from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Generic, Protocol, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")

AsyncHandler = Callable[[T], Awaitable[None]]
SyncHandler = Callable[[T], None]
Handler = Union[AsyncHandler[T], SyncHandler[T]]


class Subscription(Protocol):
    """Handle returned by ``subscribe`` that allows unsubscribing."""

    def cancel(self) -> None: ...


@dataclass(slots=True)
class _ListSubscription:
    _cancel: Callable[[], None]
    _active: bool = True

    def cancel(self) -> None:
        if not self._active:
            return
        self._active = False
        self._cancel()


class TypedEventBus(Generic[T]):
    """In-process, asyncio-friendly, typed pub/sub.

    * ``subscribe(handler)`` — returns a :class:`Subscription`
    * ``publish_and_wait(event)`` — synchronous: calls handlers directly,
      schedules async handlers as tasks when a loop is running
    * ``publish_and_forget_async(event)`` — fire-and-forget (schedules tasks)
    * ``publish_and_wait_async(event)`` — awaits all handlers
    """

    __slots__ = ("_handlers",)

    def __init__(self) -> None:
        self._handlers: list[Handler[T]] = []

    def subscribe(self, handler: Handler[T]) -> Subscription:
        self._handlers.append(handler)

        def _remove() -> None:
            try:
                self._handlers.remove(handler)
            except ValueError:
                pass

        return _ListSubscription(_cancel=_remove)

    async def _invoke(self, handler: Handler[T], event: T) -> None:
        result: Any = handler(event)
        if asyncio.iscoroutine(result):
            await result

    def publish_and_wait(self, event: T) -> None:
        """Synchronous publish: call each handler directly.

        Sync handlers are invoked inline.  Async handlers are scheduled
        as fire-and-forget tasks when a running event loop is detected;
        otherwise they are skipped with a warning.
        """
        loop: asyncio.AbstractEventLoop | None = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

        for handler in list(self._handlers):
            result: Any = handler(event)
            if asyncio.iscoroutine(result):
                if loop is not None:
                    loop.create_task(result)
                else:
                    result.close()
                    logger.warning(
                        "Skipping async handler %r — no running event loop",
                        handler,
                    )

    def publish_and_forget_async(self, event: T) -> list[asyncio.Task[None]]:
        """Fire-and-forget: schedule each handler as a background task."""
        loop = asyncio.get_running_loop()
        return [loop.create_task(self._invoke(h, event)) for h in list(self._handlers)]

    async def publish_and_wait_async(
        self, event: T, *, return_exceptions: bool = False
    ) -> None:
        """Invoke every handler and await completion.

        When ``return_exceptions=True`` failures from one subscriber do not
        cancel the others, and each swallowed exception is logged. Use this
        at hot-path publish sites (e.g. ``text_delta``) where a single flaky
        analytics subscriber should not abort the stream.
        """
        handlers = list(self._handlers)
        coros = [self._invoke(h, event) for h in handlers]
        if not coros:
            return
        if return_exceptions:
            results = await asyncio.gather(*coros, return_exceptions=True)
            for handler, result in zip(handlers, results):
                if isinstance(result, BaseException) and not isinstance(
                    result, asyncio.CancelledError
                ):
                    logger.error(
                        "Subscriber %r raised during publish; swallowing: %r",
                        handler,
                        result,
                        exc_info=result,
                    )
        else:
            await asyncio.gather(*coros)
