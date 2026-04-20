"""Subscriber that persists assistant messages in response to stream events.

Single responsibility: owns every ``unique_sdk.Message.modify_async`` call
related to a streaming response (``startedStreamingAt``, incremental text
+ references, ``stoppedStreamingAt``, ``completedAt``), plus the
``content_chunks`` used to filter references down to what was actually cited.

Attach by subscribing a single bound method per event type:

.. code-block:: python

    persister = MessagePersistingSubscriber(settings)
    bus.subscribe(persister.handle)

No internal per-stream state is required because every event carries the
``message_id``/``chat_id`` it targets; this makes the subscriber safe to
reuse across overlapping streams within the same ``UniqueSettings``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import unique_sdk

from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    filter_cited_sdk_references,
)

from ..events import StreamEnded, StreamEvent, StreamStarted, TextDelta

if TYPE_CHECKING:
    from unique_toolkit.app.unique_settings import UniqueSettings
    from unique_toolkit.content.schemas import ContentChunk


def _now_iso() -> str:
    """Return ``datetime.now(UTC)`` in the format the SDK expects."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class MessagePersistingSubscriber:
    """Translates :data:`StreamEvent` into ``unique_sdk.Message.modify_async`` calls.

    Holds the retrieved chunks for the currently active stream (keyed by
    ``message_id``) so reference filtering on :class:`TextDelta` and
    :class:`StreamEnded` uses only what was retrieved for that stream.
    """

    def __init__(self, settings: UniqueSettings) -> None:
        self._settings = settings
        self._chunks_by_message: dict[str, list[ContentChunk]] = {}

    async def handle(self, event: StreamEvent) -> None:
        """Single entry point — dispatches on event type."""
        if isinstance(event, StreamStarted):
            await self._on_started(event)
        elif isinstance(event, TextDelta):
            await self._on_text_delta(event)
        elif isinstance(event, StreamEnded):
            await self._on_ended(event)

    async def _on_started(self, event: StreamStarted) -> None:
        self._chunks_by_message[event.message_id] = list(event.content_chunks)

        # References are intentionally empty here: we only attach a
        # reference once the model has actually cited it (detected via
        # ``<sup>N</sup>`` in the normalised streaming text). Seeding all
        # retrieved chunks upfront would leak every candidate source into
        # the frontend before the model decides to use it.
        await unique_sdk.Message.modify_async(
            id=event.message_id,
            chatId=event.chat_id,
            user_id=self._settings.context.auth.user_id.get_secret_value(),
            company_id=self._settings.context.auth.company_id.get_secret_value(),
            references=[],
            startedStreamingAt=_now_iso(),  # type: ignore[arg-type]
        )

    async def _on_text_delta(self, event: TextDelta) -> None:
        chunks = self._chunks_by_message.get(event.message_id, [])

        # Using modify as it renders the references correctly while create event does not
        await unique_sdk.Message.modify_async(
            id=event.message_id,
            chatId=event.chat_id,
            user_id=self._settings.context.auth.user_id.get_secret_value(),
            company_id=self._settings.context.auth.company_id.get_secret_value(),
            text=event.full_text or None,
            originalText=event.original_text or None,
            references=filter_cited_sdk_references(chunks, event.full_text),
        )

    async def _on_ended(self, event: StreamEnded) -> None:
        chunks = self._chunks_by_message.pop(event.message_id, [])
        now = _now_iso()

        # Concatenate any appendices (e.g. a code-interpreter code block)
        # contributed by auxiliary handlers. This keeps the final persist
        # to a single Message.modify_async call — appendix-producing
        # handlers no longer need their own retrieve+modify round-trip.
        final_text = event.full_text
        if event.appendices:
            final_text = final_text + "".join(event.appendices)

        await unique_sdk.Message.modify_async(
            id=event.message_id,
            chatId=event.chat_id,
            user_id=self._settings.context.auth.user_id.get_secret_value(),
            company_id=self._settings.context.auth.company_id.get_secret_value(),
            text=final_text or None,
            originalText=event.original_text or None,
            references=filter_cited_sdk_references(chunks, event.full_text),
            stoppedStreamingAt=now,  # type: ignore[arg-type]
            completedAt=now,  # type: ignore[arg-type]
        )
