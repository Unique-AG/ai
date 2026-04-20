"""Subscriber that persists :class:`ActivityProgress` events as ``MessageLog`` entries.

Single responsibility: owns every ``unique_sdk.MessageLog.create_async`` /
``unique_sdk.MessageLog.update_async`` call triggered by tool-like activity
progress (code interpreter today, other tools in future). Keyed by
``correlation_id`` so repeated transitions for the same logical call
coalesce into one log entry that is created once and updated on changes.

No per-stream state is required beyond the in-memory log-id lookup; the
subscriber is safe to reuse across overlapping streams within the same
``UniqueSettings``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import unique_sdk

from ..events import ActivityProgress, StreamEvent

if TYPE_CHECKING:
    from unique_toolkit.app.unique_settings import UniqueSettings


class ProgressLogPersister:
    """Translates :class:`ActivityProgress` into ``MessageLog`` SDK calls.

    Private state: ``_logs_by_correlation`` mapping ``correlation_id`` to
    the SDK ``MessageLog`` returned by the most recent write. The mapping
    is how we decide between ``create_async`` (first sighting) and
    ``update_async`` (subsequent transitions), and is also used to skip
    no-op writes when a handler hasn't already deduplicated.
    """

    def __init__(self, settings: UniqueSettings) -> None:
        self._settings = settings
        self._logs_by_correlation: dict[str, unique_sdk.MessageLog] = {}

    async def handle(self, event: StreamEvent) -> None:
        """Single entry point — dispatches only on :class:`ActivityProgress`."""
        if isinstance(event, ActivityProgress):
            await self._on_activity_progress(event)

    async def _on_activity_progress(self, event: ActivityProgress) -> None:
        auth = self._settings.context.auth
        user_id = auth.user_id.get_secret_value()
        company_id = auth.company_id.get_secret_value()

        existing = self._logs_by_correlation.get(event.correlation_id)
        if existing is None:
            self._logs_by_correlation[
                event.correlation_id
            ] = await unique_sdk.MessageLog.create_async(
                user_id=user_id,
                company_id=company_id,
                **unique_sdk.MessageLog.CreateMessageLogParams(
                    messageId=event.message_id,
                    text=event.text,
                    status=event.status,
                    order=event.order,
                ),
            )
            return

        # Extra defensive dedup: handlers already skip duplicates, but a
        # custom publisher could double-fire. Cheap tuple check keeps the
        # SDK-call rate tied to real transitions.
        if existing.status == event.status and existing.text == event.text:
            return

        self._logs_by_correlation[
            event.correlation_id
        ] = await unique_sdk.MessageLog.update_async(
            user_id=user_id,
            company_id=company_id,
            message_log_id=existing.id,
            **unique_sdk.MessageLog.UpdateMessageLogParams(
                text=event.text,
                status=event.status,
            ),
        )
