"""Cancellation detection and notification for chat agent executions."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Coroutine

import unique_sdk

from unique_toolkit._common.event_bus import TypedEventBus
from unique_toolkit.chat.schemas import CancellationEvent, StoppedByUserException

logger = logging.getLogger(__name__)


class CancellationWatcher:
    """Polls the database for ``cancelledAt`` and publishes to an event bus.

    Parameters
    ----------
    bus:
        The event bus on which :class:`CancellationEvent` will be published.
    user_id, company_id, chat_id, assistant_message_id:
        Identifiers needed to retrieve the assistant message from the DB.
    """

    def __init__(
        self,
        *,
        bus: TypedEventBus[CancellationEvent],
        user_id: str,
        company_id: str,
        chat_id: str,
        assistant_message_id: str,
    ) -> None:
        self._bus = bus
        self._user_id = user_id
        self._company_id = company_id
        self._chat_id = chat_id
        self._assistant_message_id = assistant_message_id

    @property
    def on_cancellation(self) -> TypedEventBus[CancellationEvent]:
        return self._bus

    async def check_cancellation_async(self) -> None:
        """Poll the DB once and publish + raise if cancelled."""
        try:
            raw_msg = await unique_sdk.Message.retrieve_async(
                user_id=self._user_id,
                company_id=self._company_id,
                id=self._assistant_message_id,
                chatId=self._chat_id,
            )
            cancelled_at = getattr(raw_msg, "cancelledAt", None)
            if cancelled_at is not None:
                event = CancellationEvent(message_id=self._assistant_message_id)
                await self._bus.publish_and_wait(event)
                raise StoppedByUserException("User cancelled the agent execution")
        except StoppedByUserException:
            raise
        except Exception as exc:
            logger.warning("Failed to check cancellation: %s: %s", type(exc).__name__, exc)

    def check_cancellation(self) -> None:
        """Synchronous single-shot check (no event bus notification)."""
        try:
            raw_msg = unique_sdk.Message.retrieve(
                user_id=self._user_id,
                company_id=self._company_id,
                id=self._assistant_message_id,
                chatId=self._chat_id,
            )
            cancelled_at = getattr(raw_msg, "cancelledAt", None)
            if cancelled_at is not None:
                raise StoppedByUserException("User cancelled the agent execution")
        except StoppedByUserException:
            raise
        except Exception as exc:
            logger.warning("Failed to check cancellation: %s: %s", type(exc).__name__, exc)

    async def run_with_cancellation(
        self,
        coroutine: Coroutine[Any, Any, Any],
        poll_interval: float = 2.0,
    ) -> Any:
        """Run *coroutine* while polling for cancellation in the background.

        If ``cancelledAt`` is detected the running task is cancelled via
        ``asyncio.Task.cancel()``, subscribers are notified through the bus,
        and :class:`StoppedByUserException` is raised.
        """
        task = asyncio.ensure_future(coroutine)

        async def _watcher() -> None:
            while not task.done():
                try:
                    await self.check_cancellation_async()
                except StoppedByUserException:
                    task.cancel()
                    return
                await asyncio.sleep(poll_interval)

        watcher = asyncio.ensure_future(_watcher())
        try:
            return await task
        except asyncio.CancelledError:
            raise StoppedByUserException("User cancelled the agent execution")
        finally:
            watcher.cancel()
            try:
                await watcher
            except asyncio.CancelledError:
                pass
