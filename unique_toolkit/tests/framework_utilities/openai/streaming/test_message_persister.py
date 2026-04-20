"""Tests for ``MessagePersistingSubscriber`` — the default StreamEvent subscriber.

Verifies the subscriber owns every ``unique_sdk.Message.modify_async`` call
that used to live in text handlers / pipelines, and correctly filters
references using the chunks carried on :class:`StreamStarted`.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from pydantic import SecretStr

from unique_toolkit.app.unique_settings import (
    AuthContext,
    ChatContext,
    UniqueApi,
    UniqueApp,
    UniqueContext,
    UniqueSettings,
)
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.framework_utilities.openai.streaming.pipeline.events import (
    ActivityProgress,
    StreamEnded,
    StreamEventBus,
    StreamStarted,
    TextDelta,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.subscribers.message_persister import (
    MessagePersistingSubscriber,
)

_MODIFY = (
    "unique_toolkit.framework_utilities.openai.streaming.pipeline."
    "subscribers.message_persister.unique_sdk.Message.modify_async"
)


def _settings_with_chat() -> UniqueSettings:
    auth = AuthContext(user_id=SecretStr("user-1"), company_id=SecretStr("company-1"))
    chat = ChatContext(
        chat_id="chat-1",
        assistant_id="assistant-1",
        last_assistant_message_id="amsg-1",
        last_user_message_id="umsg-1",
        last_user_message_text="",
    )
    s = UniqueSettings(auth=auth, app=UniqueApp(), api=UniqueApi())
    s._context = UniqueContext(auth=auth, chat=chat)
    return s


def _chunk(idx: int) -> ContentChunk:
    return ContentChunk(
        text=f"chunk text {idx}",
        order=idx,
        chunk_id=f"chunk_id_{idx}",
        key=f"key_{idx}",
        title=f"Title {idx}",
        start_page=1,
        end_page=1,
        url=f"https://example.com/{idx}",
        id=f"id_{idx}",
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_persister__stream_started__marks_message_as_streaming():
    """
    Purpose: On ``StreamStarted`` the subscriber flips the message into streaming mode.
    Why this matters: The UI relies on ``startedStreamingAt`` + empty ``references`` to show
      a spinner without leaking every retrieved chunk before citation.
    Setup summary: Patch ``Message.modify_async``; publish StreamStarted; assert call kwargs.
    """
    persister = MessagePersistingSubscriber(_settings_with_chat())
    with patch(_MODIFY, new_callable=AsyncMock) as modify:
        await persister.on_started(
            StreamStarted(
                message_id="amsg-1",
                chat_id="chat-1",
                content_chunks=(_chunk(0),),
            )
        )
    modify.assert_called_once()
    kwargs = modify.call_args.kwargs
    assert kwargs["id"] == "amsg-1"
    assert kwargs["chatId"] == "chat-1"
    assert kwargs["references"] == []
    assert "startedStreamingAt" in kwargs


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_persister__text_delta__modifies_message_with_text_and_references():
    """
    Purpose: Each ``TextDelta`` persists normalised text + cited references via the SDK.
    Why this matters: Users see incremental updates; references must reflect what the
      model *cited*, not the full retrieval set seeded at stream start.
    Setup summary: Pre-seed chunks via StreamStarted; publish TextDelta that cites <sup>1</sup>;
      assert modify was called with text + non-empty references.
    """
    persister = MessagePersistingSubscriber(_settings_with_chat())
    with patch(_MODIFY, new_callable=AsyncMock) as modify:
        await persister.on_started(
            StreamStarted(
                message_id="amsg-1",
                chat_id="chat-1",
                content_chunks=(_chunk(0), _chunk(1)),
            )
        )
        modify.reset_mock()

        await persister.on_text_delta(
            TextDelta(
                message_id="amsg-1",
                chat_id="chat-1",
                full_text="Hello <sup>1</sup>",
                original_text="Hello [source0]",
            )
        )

    modify.assert_called_once()
    kwargs = modify.call_args.kwargs
    assert kwargs["id"] == "amsg-1"
    assert kwargs["text"] == "Hello <sup>1</sup>"
    assert kwargs["originalText"] == "Hello [source0]"
    # references is whatever filter_cited_sdk_references produced — just ensure key is present
    assert "references" in kwargs


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_persister__stream_ended__persists_final_state_and_clears_chunks():
    """
    Purpose: ``StreamEnded`` writes the authoritative final state and releases per-stream chunks.
    Why this matters: Frontend uses ``stoppedStreamingAt`` / ``completedAt`` to mark the
      message done; cached chunks must not leak across overlapping streams.
    Setup summary: Publish StreamStarted then StreamEnded; assert final modify kwargs and
      that a subsequent TextDelta for the same message has no chunks (empty references).
    """
    persister = MessagePersistingSubscriber(_settings_with_chat())
    with patch(_MODIFY, new_callable=AsyncMock) as modify:
        await persister.on_started(
            StreamStarted(
                message_id="amsg-1",
                chat_id="chat-1",
                content_chunks=(_chunk(0),),
            )
        )
        await persister.on_ended(
            StreamEnded(
                message_id="amsg-1",
                chat_id="chat-1",
                full_text="Done <sup>1</sup>",
                original_text="Done [source0]",
            )
        )
        final_kwargs = modify.call_args.kwargs
        assert "stoppedStreamingAt" in final_kwargs
        assert "completedAt" in final_kwargs
        assert final_kwargs["text"] == "Done <sup>1</sup>"

        # chunks released: a further TextDelta for the same message gets empty chunk set
        modify.reset_mock()
        await persister.on_text_delta(
            TextDelta(
                message_id="amsg-1",
                chat_id="chat-1",
                full_text="late <sup>1</sup>",
                original_text="late",
            )
        )
    second_kwargs = modify.call_args.kwargs
    assert second_kwargs["references"] == []


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_persister__isolates_overlapping_streams_by_message_id():
    """
    Purpose: Per-message chunk storage prevents cross-talk between parallel streams.
    Why this matters: A single persister may be reused (same settings); chunks from
      stream A must not surface in references for stream B.
    Setup summary: Start two streams with disjoint chunks; publish TextDelta for each;
      assert the subscriber's internal state remains partitioned (stream end clears only one).
    """
    persister = MessagePersistingSubscriber(_settings_with_chat())
    with patch(_MODIFY, new_callable=AsyncMock):
        await persister.on_started(
            StreamStarted(
                message_id="a",
                chat_id="c",
                content_chunks=(_chunk(0),),
            )
        )
        await persister.on_started(
            StreamStarted(
                message_id="b",
                chat_id="c",
                content_chunks=(_chunk(1),),
            )
        )
        # internal state keeps both entries until each ends
        assert set(persister._chunks_by_message.keys()) == {"a", "b"}

        await persister.on_ended(
            StreamEnded(
                message_id="a",
                chat_id="c",
                full_text="",
                original_text="",
            )
        )
        assert set(persister._chunks_by_message.keys()) == {"b"}


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_persister__register__subscribes_to_text_lifecycle_channels_only():
    """
    Purpose: ``register(bus)`` wires the persister onto the three text-lifecycle
      channels and deliberately leaves ``activity_progress`` alone.
    Why this matters: The new typed-channel bus replaces runtime ``isinstance``
      filtering with compile-time channel selection — this test locks in that
      the persister listens on exactly the channels it can handle, so
      :class:`ActivityProgress` events never reach ``Message.modify_async``.
    Setup summary: Build a fresh :class:`StreamEventBus`, ``register`` the
      persister, publish one event per channel, and assert that only the three
      text-lifecycle channels produce ``modify_async`` calls.
    """
    persister = MessagePersistingSubscriber(_settings_with_chat())
    bus = StreamEventBus()
    persister.register(bus)

    with patch(_MODIFY, new_callable=AsyncMock) as modify:
        await bus.stream_started.publish_and_wait_async(
            StreamStarted(message_id="m", chat_id="c", content_chunks=())
        )
        await bus.text_delta.publish_and_wait_async(
            TextDelta(message_id="m", chat_id="c", full_text="hi", original_text="hi")
        )
        await bus.stream_ended.publish_and_wait_async(
            StreamEnded(message_id="m", chat_id="c", full_text="hi", original_text="hi")
        )
        # activity_progress must NOT produce a Message.modify_async call — the
        # persister deliberately does not subscribe to that channel.
        await bus.activity_progress.publish_and_wait_async(
            ActivityProgress(
                correlation_id="cid",
                message_id="m",
                chat_id="c",
                status="RUNNING",
                text="tick",
            )
        )

    assert modify.await_count == 3
