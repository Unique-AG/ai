"""Subscriber that persists assistant messages in response to stream events.

Single responsibility: owns every ``unique_sdk.Message.modify_async`` call
related to a streaming response (``startedStreamingAt``, incremental text
+ references, ``stoppedStreamingAt``, ``completedAt``), plus the
``content_chunks`` used to filter references down to what was actually cited.

Attach by calling :meth:`register` once on the owned bus:

.. code-block:: python

    persister = MessagePersistingSubscriber(settings)
    persister.register(orchestrator.bus)

No internal per-stream state is required beyond the per-message chunk
lookup because every event carries the ``message_id``/``chat_id`` it
targets; this makes the subscriber safe to reuse across overlapping
streams within the same ``UniqueSettings``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import unique_sdk

from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    filter_cited_sdk_references,
)

from ..events import StreamEnded, StreamEventBus, StreamStarted, TextDelta

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from unique_toolkit.app.unique_settings import UniqueSettings
    from unique_toolkit.content.schemas import ContentChunk


def _now_iso() -> str:
    """Return ``datetime.now(UTC)`` in the format the SDK expects."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class MessagePersistingSubscriber:
    """Translates text lifecycle events into ``unique_sdk.Message.modify_async`` calls.

    Holds the retrieved chunks for the currently active stream (keyed by
    ``message_id``) so reference filtering on :class:`TextDelta` and
    :class:`StreamEnded` uses only what was retrieved for that stream.

    ``persist_every_n_deltas`` throttles SDK writes on the
    :class:`TextDelta` hot path. The default (``1``) preserves the original
    behaviour — every flush from the handler produces one write. The
    handler's own ``send_every_n_events`` knob already throttles on the
    upstream side (content chunks per flush); this subscriber-level knob
    adds a secondary throttle measured in *flushes*. Combine them when the
    handler is configured for low-latency flushes but downstream SDK
    pressure needs reducing. The final :class:`StreamEnded` write is
    always performed and is authoritative, so throttling deltas only ever
    coarsens intermediate UI updates — it never drops data.
    """

    def __init__(
        self,
        settings: UniqueSettings,
        *,
        persist_every_n_deltas: int = 1,
    ) -> None:
        self._settings = settings
        self._chunks_by_message: dict[str, list[ContentChunk]] = {}
        self._persist_every_n_deltas = max(1, persist_every_n_deltas)
        # Per-message counter so overlapping streams on the same subscriber
        # instance don't share a throttle boundary.
        self._delta_counter_by_message: dict[str, int] = {}

    def register(self, bus: StreamEventBus) -> None:
        """Subscribe this persister to the text lifecycle channels on ``bus``.

        Intentionally does not touch :attr:`StreamEventBus.activity_progress`:
        progress logs are owned by :class:`ProgressLogPersister`.
        """
        bus.stream_started.subscribe(self.on_started)
        bus.text_delta.subscribe(self.on_text_delta)
        bus.stream_ended.subscribe(self.on_ended)

    async def on_started(self, event: StreamStarted) -> None:
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

    async def on_text_delta(self, event: TextDelta) -> None:
        chunks = self._chunks_by_message.get(event.message_id, [])

        # Apply the per-subscriber throttle. We only skip intermediate
        # writes — the authoritative final state ships on :class:`StreamEnded`.
        count = self._delta_counter_by_message.get(event.message_id, 0) + 1
        self._delta_counter_by_message[event.message_id] = count
        if count % self._persist_every_n_deltas != 0:
            return

        # Incremental writes are the hot path: a transient SDK failure here
        # must not abort the stream loop. The authoritative final state is
        # written again in :meth:`on_ended`, so a dropped delta degrades
        # to a slightly coarser UI update rather than data loss.
        try:
            await unique_sdk.Message.modify_async(
                id=event.message_id,
                chatId=event.chat_id,
                user_id=self._settings.context.auth.user_id.get_secret_value(),
                company_id=self._settings.context.auth.company_id.get_secret_value(),
                text=event.full_text or None,
                originalText=event.original_text or None,
                references=filter_cited_sdk_references(chunks, event.full_text),
            )
        except Exception as exc:
            _LOGGER.warning(
                "MessagePersistingSubscriber: incremental text_delta write "
                "failed for message %r; continuing stream. Error: %r",
                event.message_id,
                exc,
            )

    async def on_ended(self, event: StreamEnded) -> None:
        chunks = self._chunks_by_message.pop(event.message_id, [])
        self._delta_counter_by_message.pop(event.message_id, None)
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
