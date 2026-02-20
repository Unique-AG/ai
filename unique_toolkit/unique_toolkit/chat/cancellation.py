"""Cancellation detection and notification for chat agent executions."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Coroutine, TypeVar, overload

import unique_sdk

from unique_toolkit._common.event_bus import TypedEventBus


@dataclass(frozen=True, slots=True)
class CancellationEvent:
    """Published on the cancellation event bus when a user abort is detected."""

    message_id: str

T = TypeVar("T")

logger = logging.getLogger(__name__)


class CancellationWatcher:
    """Polls the database for ``cancelledAt`` and publishes to an event bus.

    The watcher never raises exceptions for cancellation. Instead it:
    - publishes a :class:`CancellationEvent` on the bus
    - sets :attr:`is_cancelled` to ``True``

    Callers inspect :attr:`is_cancelled` to decide whether to stop.
    """

    def __init__(
        self,
        *,
        user_id: str,
        company_id: str,
        chat_id: str,
        assistant_message_id: str,
    ) -> None:
        self._bus: TypedEventBus[CancellationEvent] = TypedEventBus()
        self._user_id = user_id
        self._company_id = company_id
        self._chat_id = chat_id
        self._assistant_message_id = assistant_message_id
        self._cancelled = False

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    @property
    def on_cancellation(self) -> TypedEventBus[CancellationEvent]:
        return self._bus

    async def check_cancellation_async(self) -> bool:
        """Poll the DB once.  Returns ``True`` if the message was cancelled.

        When cancellation is detected for the first time, all subscribers
        on the bus are notified (awaited) before this method returns.
        """
        if self._cancelled:
            return True
        try:
            raw_msg = await unique_sdk.Message.retrieve_async(
                user_id=self._user_id,
                company_id=self._company_id,
                id=self._assistant_message_id,
                chatId=self._chat_id,
            )
            cancelled_at = getattr(raw_msg, "cancelledAt", None)
            if cancelled_at is not None:
                self._cancelled = True
                event = CancellationEvent(message_id=self._assistant_message_id)
                await self._bus.publish_and_wait_async(event)
                return True
        except Exception as exc:
            logger.warning(
                "Failed to check cancellation: %s: %s", type(exc).__name__, exc
            )
        return False

    def check_cancellation(self) -> bool:
        """Synchronous single-shot check.

        Returns ``True`` if the message was cancelled.  Subscribers are
        notified via :meth:`TypedEventBus.publish_and_wait` (sync handlers
        are called inline; async handlers are scheduled as tasks when a
        running event loop is detected).
        """
        if self._cancelled:
            return True
        try:
            raw_msg = unique_sdk.Message.retrieve(
                user_id=self._user_id,
                company_id=self._company_id,
                id=self._assistant_message_id,
                chatId=self._chat_id,
            )
            cancelled_at = getattr(raw_msg, "cancelledAt", None)
            if cancelled_at is not None:
                self._cancelled = True
                event = CancellationEvent(message_id=self._assistant_message_id)
                self._bus.publish_and_wait(event)
                return True
        except Exception as exc:
            logger.warning(
                "Failed to check cancellation: %s: %s", type(exc).__name__, exc
            )
        return False

    @overload
    async def run_with_cancellation(
        self,
        coroutine: Coroutine[Any, Any, T],
        *,
        poll_interval: float = ...,
        cancel_result: T,
    ) -> T: ...

    @overload
    async def run_with_cancellation(
        self,
        coroutine: Coroutine[Any, Any, T],
        *,
        poll_interval: float = ...,
    ) -> T | None: ...

    async def run_with_cancellation(
        self,
        coroutine: Coroutine[Any, Any, Any],
        *,
        poll_interval: float = 2.0,
        cancel_result: Any = None,
    ) -> Any:
        """Run *coroutine* while polling for cancellation in the background.

        When cancelled, subscribers are notified via the bus and
        :attr:`is_cancelled` is set to ``True``.

        Args:
            coroutine: The async coroutine to execute.
            poll_interval: How often (in seconds) to poll for cancellation.
            cancel_result: Value to return when cancelled.  When provided
                the return type matches the coroutine's return type so
                callers don't need a ``None`` check.

        Returns:
            The coroutine's result on success, or *cancel_result* if
            cancelled (defaults to ``None``).
        """
        task = asyncio.create_task(coroutine)

        async def _watcher() -> None:
            while not task.done():
                cancelled = await self.check_cancellation_async()
                if cancelled:
                    task.cancel()
                    return
                await asyncio.sleep(poll_interval)

        watcher = asyncio.create_task(_watcher())
        try:
            return await task
        except asyncio.CancelledError:
            return cancel_result
        finally:
            watcher.cancel()
            try:
                await watcher
            except asyncio.CancelledError:
                pass
