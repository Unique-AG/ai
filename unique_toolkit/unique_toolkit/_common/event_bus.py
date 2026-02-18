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
    * ``publish(event)`` — fire-and-forget (schedules tasks)
    * ``publish_and_wait(event)`` — awaits all handlers
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

    def publish(self, event: T) -> list[asyncio.Task[None]]:
        """Fire-and-forget: schedule each handler as a background task."""
        loop = asyncio.get_running_loop()
        return [loop.create_task(self._invoke(h, event)) for h in list(self._handlers)]

    async def publish_and_wait(
        self, event: T, *, return_exceptions: bool = False
    ) -> None:
        """Invoke every handler and await completion."""
        coros = [self._invoke(h, event) for h in list(self._handlers)]
        if coros:
            await asyncio.gather(*coros, return_exceptions=return_exceptions)
