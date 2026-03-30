"""Tests for PipelineResponsesStreamingHandler."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai.types.responses import (
    Response,
    ResponseCompletedEvent,
    ResponseOutputMessage,
    ResponseStreamEvent,
    ResponseTextDeltaEvent,
)
from openai.types.responses.response_output_text import ResponseOutputText
from openai.types.responses.response_usage import (
    InputTokensDetails,
    OutputTokensDetails,
    ResponseUsage,
)

from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses_streaming_handler import (
    PipelineResponsesStreamingHandler,
)
from unique_toolkit.language_model.schemas import ResponsesLanguageModelStreamResponse


def _make_settings() -> MagicMock:
    """Build a minimal ``UniqueSettings`` mock with chat context."""
    settings = MagicMock()
    settings.context.chat.chat_id = "chat-1"
    settings.context.chat.last_assistant_message_id = "msg-1"
    settings.context.auth.user_id.get_secret_value.return_value = "user-1"
    settings.context.auth.company_id.get_secret_value.return_value = "company-1"
    return settings


def _text_delta(delta: str, seq: int) -> ResponseTextDeltaEvent:
    return ResponseTextDeltaEvent(
        content_index=0,
        delta=delta,
        item_id="item-1",
        logprobs=[],
        output_index=0,
        sequence_number=seq,
        type="response.output_text.delta",
    )


def _completed_event(text: str, seq: int) -> ResponseCompletedEvent:
    usage = ResponseUsage(
        input_tokens=5,
        input_tokens_details=InputTokensDetails(cached_tokens=0),
        output_tokens=10,
        output_tokens_details=OutputTokensDetails(reasoning_tokens=0),
        total_tokens=15,
    )
    output_message = ResponseOutputMessage(
        id="out-1",
        type="message",
        role="assistant",
        status="completed",
        content=[
            ResponseOutputText(type="output_text", text=text, annotations=[]),
        ],
    )
    response = Response.model_construct(
        usage=usage,
        output=[output_message],
    )
    return ResponseCompletedEvent.model_construct(
        response=response,
        sequence_number=seq,
        type="response.completed",
    )


async def _fake_stream(
    events: list[ResponseStreamEvent],
) -> AsyncIterator[ResponseStreamEvent]:
    for e in events:
        yield e


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.modify_async", new_callable=AsyncMock)
@patch("unique_sdk.Message.create_event_async", new_callable=AsyncMock)
async def test_AI_handler__streams_text_and_returns_result__happy_path(
    mock_create_event: AsyncMock,
    mock_modify: AsyncMock,
) -> None:
    """
    Purpose: Verify the handler streams text deltas and returns a complete result.
    Why this matters: Core contract for pipeline-backed Responses streaming.
    Setup summary: Two text deltas + completed event, mock SDK calls, assert result fields.
    """
    # Arrange
    settings = _make_settings()
    events = [
        _text_delta("Hello", 0),
        _text_delta(" world", 1),
        _completed_event("Hello world", 2),
    ]

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=_fake_stream(events))

    handler = PipelineResponsesStreamingHandler(settings)

    with patch(
        "unique_toolkit.framework_utilities.openai.streaming.pipeline."
        "responses_streaming_handler.get_async_openai_client",
        return_value=mock_client,
    ):
        # Act
        result = await handler.complete_with_references_async(
            model_name="test-model",
            messages="Hello",
        )

    # Assert
    assert isinstance(result, ResponsesLanguageModelStreamResponse)
    assert result.message.text == "Hello world"
    assert result.usage is not None
    assert result.usage.total_tokens == 15
    assert len(result.output) == 1
    mock_modify.assert_awaited_once()
    assert mock_create_event.await_count >= 1


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.modify_async", new_callable=AsyncMock)
@patch("unique_sdk.Message.create_event_async", new_callable=AsyncMock)
async def test_AI_handler__resolves_references__when_chunks_provided(
    mock_create_event: AsyncMock,
    mock_modify: AsyncMock,
) -> None:
    """
    Purpose: Verify post-stream reference resolution runs when content_chunks are given.
    Why this matters: References must be attached to the message for the frontend to render footnotes.
    Setup summary: Stream text containing [1], provide a content chunk, assert references are set.
    """
    # Arrange
    settings = _make_settings()
    streamed_text = "Answer is here [source 1]."
    events = [
        _text_delta(streamed_text, 0),
        _completed_event(streamed_text, 1),
    ]

    chunks = [
        ContentChunk(id="chunk-1", text="Source content", key="k1", chunk_id="c1"),
    ]

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=_fake_stream(events))

    handler = PipelineResponsesStreamingHandler(settings)

    with patch(
        "unique_toolkit.framework_utilities.openai.streaming.pipeline."
        "responses_streaming_handler.get_async_openai_client",
        return_value=mock_client,
    ):
        # Act
        result = await handler.complete_with_references_async(
            model_name="test-model",
            messages="What is the answer?",
            content_chunks=chunks,
        )

    # Assert
    assert result.message.references is not None
    assert len(result.message.references) > 0
    assert "[1]" not in (result.message.content or "")


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.modify_async", new_callable=AsyncMock)
@patch("unique_sdk.Message.create_event_async", new_callable=AsyncMock)
async def test_AI_handler__skips_references__when_config_disables_resolution(
    mock_create_event: AsyncMock,
    mock_modify: AsyncMock,
) -> None:
    """
    Purpose: Verify no reference resolution when requires_reference_resolution is False.
    Why this matters: A2A and other paths do not need post-stream resolution.
    Setup summary: Use a config with requires_reference_resolution=False, assert no references.
    """
    # Arrange
    settings = _make_settings()
    events = [
        _text_delta("No refs here", 0),
        _completed_event("No refs here", 1),
    ]

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=_fake_stream(events))

    handler = PipelineResponsesStreamingHandler(
        settings,
        normalization_patterns=[],
        resolve_references=False,
    )

    chunks = [
        ContentChunk(id="chunk-1", text="Unused", key="k1", chunk_id="c1"),
    ]

    with patch(
        "unique_toolkit.framework_utilities.openai.streaming.pipeline."
        "responses_streaming_handler.get_async_openai_client",
        return_value=mock_client,
    ):
        # Act
        result = await handler.complete_with_references_async(
            model_name="test-model",
            messages="Hello",
            content_chunks=chunks,
        )

    # Assert — references should be empty (default) since resolution was skipped
    assert result.message.references == []


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_handler__raises__when_no_chat_context() -> None:
    """
    Purpose: Verify handler raises ValueError when chat context is missing.
    Why this matters: Prevents cryptic errors deep in SDK calls.
    Setup summary: Create settings with chat=None, assert ValueError.
    """
    # Arrange
    settings = MagicMock()
    settings.context.chat = None

    handler = PipelineResponsesStreamingHandler(settings)

    # Act & Assert
    with pytest.raises(ValueError, match="Chat context is not set"):
        await handler.complete_with_references_async(
            model_name="test-model",
            messages="Hello",
        )
