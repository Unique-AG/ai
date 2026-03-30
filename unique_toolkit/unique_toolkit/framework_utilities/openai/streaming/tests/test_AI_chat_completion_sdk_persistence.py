"""Tests for ChatCompletionSdkPersistence."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from openai.types.chat.chat_completion_chunk import (
    ChatCompletionChunk,
    Choice,
    ChoiceDelta,
)

from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    StreamingReplacerProtocol,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completion_sdk_persistence import (
    ChatCompletionSdkPersistence,
)


def _content_chunk(
    content: str | None, finish_reason: str | None = None
) -> ChatCompletionChunk:
    return ChatCompletionChunk.model_construct(
        id="c1",
        choices=[
            Choice.model_construct(
                delta=ChoiceDelta.model_construct(content=content, tool_calls=None),
                finish_reason=finish_reason,
                index=0,
            )
        ],
        created=0,
        model="m",
        object="chat.completion.chunk",
    )


def _empty_chunk() -> ChatCompletionChunk:
    return ChatCompletionChunk.model_construct(
        id="c-empty",
        choices=[],
        created=0,
        model="m",
        object="chat.completion.chunk",
    )


class _PassthroughReplacer(StreamingReplacerProtocol):
    """Replacer that records calls without modifying text."""

    def __init__(self) -> None:
        self.processed: list[str] = []
        self.flushed = False

    def process(self, delta: str) -> str:
        self.processed.append(delta)
        return delta

    def flush(self) -> str:
        self.flushed = True
        return ""


class _AppendingReplacer(StreamingReplacerProtocol):
    """Replacer that appends a suffix to each delta to verify chain ordering."""

    def __init__(self, suffix: str) -> None:
        self._suffix = suffix

    def process(self, delta: str) -> str:
        return delta + self._suffix if delta else delta

    def flush(self) -> str:
        return ""


class _BufferedTailReplacer(StreamingReplacerProtocol):
    """Replacer that buffers all input and releases it only on flush (simulates tail buffer)."""

    def __init__(self) -> None:
        self._buf = ""

    def process(self, delta: str) -> str:
        self._buf += delta
        return ""

    def flush(self) -> str:
        out, self._buf = self._buf, ""
        return out


# ---------------------------------------------------------------------------
# __init__: raises when chat context is missing
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_init__raises_value_error__when_chat_context_is_none(
    test_settings_no_chat: UniqueSettings,
) -> None:
    """
    Purpose: Verify ChatCompletionSdkPersistence raises ValueError if chat is None.
    Why this matters: The persistence layer unconditionally uses chat IDs; a None
        context would cause a hard crash deep in SDK calls.
    Setup summary: Construct with settings.context.chat=None, assert ValueError.
    """
    with pytest.raises(ValueError, match="Chat context is required"):
        ChatCompletionSdkPersistence(test_settings_no_chat, replacers=[])


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_reset__clears_original_and_full_text__after_accumulation(
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify reset() wipes both text buffers so sequential reuse starts fresh.
    Why this matters: Stale text from a prior stream appearing in a new stream would
        corrupt the message displayed to the user.
    Setup summary: Simulate on_event accumulation by calling reset after, assert empty.
    """
    persistence = ChatCompletionSdkPersistence(test_settings, replacers=[])
    persistence._accumulator._full_text = "prior text"
    persistence._full_text = "prior replaced"

    persistence.reset()

    assert persistence._accumulator._full_text == ""
    assert persistence._full_text == ""


# ---------------------------------------------------------------------------
# on_event(): accumulation and replacers
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.create_event_async", new_callable=AsyncMock)
async def test_AI_on_event__accumulates_original_and_full_text__for_each_delta(
    mock_emit: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify on_event() appends content to both _original_text and _full_text.
    Why this matters: The SDK event payload requires both the raw text (originalText)
        and the replaced text (text); both must be tracked independently.
    Setup summary: Two chunks, no replacers, assert both text fields concatenated.
    """
    persistence = ChatCompletionSdkPersistence(test_settings, replacers=[])

    await persistence.on_event(_content_chunk("Hello"), index=0)
    await persistence.on_event(_content_chunk(" world"), index=1)

    assert persistence._accumulator.full_text == "Hello world"
    assert persistence._full_text == "Hello world"


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.create_event_async", new_callable=AsyncMock)
async def test_AI_on_event__applies_replacers_to_full_text__not_original(
    mock_emit: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify replacers modify _full_text but leave _original_text unchanged.
    Why this matters: The SDK event must expose both the raw and replaced text; applying
        replacers to original_text would destroy the pre-replacement record.
    Setup summary: AppendingReplacer that adds "X" suffix, assert original unchanged and
        full_text has the suffix.
    """
    replacer = _AppendingReplacer("X")
    persistence = ChatCompletionSdkPersistence(test_settings, replacers=[replacer])

    await persistence.on_event(_content_chunk("Hi"), index=0)

    assert persistence._accumulator.full_text == "Hi"
    assert persistence._full_text == "HiX"


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.create_event_async", new_callable=AsyncMock)
async def test_AI_on_event__skips_empty_choices_chunk__without_emitting(
    mock_emit: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify on_event() ignores chunks with no choices (e.g. usage-only chunks).
    Why this matters: Processing an empty choices list would cause an IndexError or
        silently add empty text to the buffers.
    Setup summary: Apply an empty-choices chunk, assert no SDK emit and empty buffers.
    """
    persistence = ChatCompletionSdkPersistence(test_settings, replacers=[])

    await persistence.on_event(_empty_chunk(), index=0)

    assert persistence._full_text == ""
    mock_emit.assert_not_awaited()


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.create_event_async", new_callable=AsyncMock)
async def test_AI_on_event__emits_sdk_event__every_send_every_n_events(
    mock_emit: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify the throttle emits exactly once every N events.
    Why this matters: Emitting on every chunk can flood the SDK with messages;
        the throttle reduces round-trips without losing content.
    Setup summary: send_every_n_events=2, apply 4 chunks, assert exactly 2 SDK calls.
    """
    persistence = ChatCompletionSdkPersistence(
        test_settings, replacers=[], send_every_n_events=2
    )

    for i in range(4):
        await persistence.on_event(_content_chunk(f"t{i}"), index=i)

    assert mock_emit.await_count == 2


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.create_event_async", new_callable=AsyncMock)
async def test_AI_on_event__emits_every_chunk__when_send_every_n_events_is_one(
    mock_emit: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify default behaviour emits on every event (send_every_n_events=1).
    Why this matters: The default low-latency setting must keep the UI up to date
        with every received token.
    Setup summary: Three chunks at default throttle=1, assert 3 SDK calls.
    """
    persistence = ChatCompletionSdkPersistence(test_settings, replacers=[])

    for i in range(3):
        await persistence.on_event(_content_chunk(f"t{i}"), index=i)

    assert mock_emit.await_count == 3


# ---------------------------------------------------------------------------
# on_stream_end(): cascade flush
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.create_event_async", new_callable=AsyncMock)
async def test_AI_on_stream_end__flushes_replacers__and_emits_remaining_text(
    mock_emit: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify on_stream_end() cascade-flushes replacers and emits an event
        for any text released by the flush.
    Why this matters: Replacers like StreamingPatternReplacer hold a tail buffer;
        without a flush the last references/tokens would never reach the SDK.
    Setup summary: BufferedTailReplacer retains all text in process(), releases on flush.
        Assert that after on_stream_end the text is emitted.
    """
    tail_replacer = _BufferedTailReplacer()
    persistence = ChatCompletionSdkPersistence(test_settings, replacers=[tail_replacer])

    # on_event puts "Hello" into the buffer but nothing is released to _full_text
    await persistence.on_event(_content_chunk("Hello"), index=0)
    assert persistence._full_text == ""

    await persistence.on_stream_end()

    # After flush, _full_text should contain "Hello" and an event should be emitted
    assert persistence._full_text == "Hello"
    mock_emit.assert_awaited()


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.create_event_async", new_callable=AsyncMock)
async def test_AI_on_stream_end__does_not_emit__when_nothing_remains_after_flush(
    mock_emit: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify on_stream_end() does not emit an SDK event when all replacers
        return empty strings from flush().
    Why this matters: A spurious final emit with no new text would flicker the UI.
    Setup summary: PassthroughReplacer (flush returns ""), assert no extra emit in on_stream_end.
    """
    replacer = _PassthroughReplacer()
    persistence = ChatCompletionSdkPersistence(
        test_settings, replacers=[replacer], send_every_n_events=100
    )

    # No on_event calls — nothing to flush
    await persistence.on_stream_end()

    mock_emit.assert_not_awaited()
    assert replacer.flushed is True


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.create_event_async", new_callable=AsyncMock)
async def test_AI_on_stream_end__cascade_feeds_upstream_tail_to_downstream_replacer(
    mock_emit: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify that the cascade flush correctly feeds an upstream replacer's
        flush output through the downstream replacer's process() before the downstream
        replacer is itself flushed.
    Why this matters: This is the key correctness invariant — without cascade, the
        BufferedTailReplacer's tail would bypass any downstream replacer (e.g.
        ReferenceResolutionReplacer), silently dropping end-of-stream citations.
    Setup summary: Chain [BufferedTailReplacer, PassthroughReplacer]. The tail replacer
        holds all text; its flush output must appear in the passthrough's processed list.
    """
    tail_replacer = _BufferedTailReplacer()
    pass_replacer = _PassthroughReplacer()
    persistence = ChatCompletionSdkPersistence(
        test_settings, replacers=[tail_replacer, pass_replacer]
    )

    await persistence.on_event(_content_chunk("tail-text"), index=0)
    await persistence.on_stream_end()

    # The passthrough replacer should have seen "tail-text" from the cascade
    assert "tail-text" in pass_replacer.processed
