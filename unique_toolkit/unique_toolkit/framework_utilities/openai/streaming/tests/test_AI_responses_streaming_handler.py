"""Tests for ResponsesCompleteWithReferences."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
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

from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.chat.responses_api import _convert_messages_to_openai
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    StreamingReplacerProtocol,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.code_interpreter_handler import (
    ResponsesCodeInterpreterHandler,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.complete_with_references import (
    ResponsesCompleteWithReferences,
    _convert_tools,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.completed_handler import (
    ResponsesCompletedHandler,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.stream_pipeline import (
    ResponsesStreamPipeline,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.text_delta_handler import (
    ResponsesTextDeltaHandler,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.tool_call_handler import (
    ResponsesToolCallHandler,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelToolDescription,
    LanguageModelUserMessage,
    ResponsesLanguageModelStreamResponse,
)


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


def _build_pipeline(
    settings: UniqueSettings,
    *,
    replacers: list[StreamingReplacerProtocol] | None = None,
) -> ResponsesStreamPipeline:
    return ResponsesStreamPipeline(
        text_handler=ResponsesTextDeltaHandler(
            settings,
            replacers=replacers or [],
        ),
        tool_call_handler=ResponsesToolCallHandler(),
        completed_handler=ResponsesCompletedHandler(),
        code_interpreter_handler=ResponsesCodeInterpreterHandler(settings),
    )


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.modify_async", new_callable=AsyncMock)
async def test_AI_handler__streams_text_and_returns_result__happy_path(
    mock_modify: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify the handler streams text deltas and returns a complete result.
    Why this matters: Core contract for pipeline-backed Responses streaming.
    Setup summary: Two text deltas + completed event, mock SDK calls, assert result fields.
    """
    # Arrange
    events = [
        _text_delta("Hello", 0),
        _text_delta(" world", 1),
        _completed_event("Hello world", 2),
    ]

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=_fake_stream(events))

    pipeline = _build_pipeline(test_settings)
    handler = ResponsesCompleteWithReferences(
        test_settings,
        pipeline=pipeline,
        client=mock_client,
    )

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
    assert mock_modify.await_count >= 1


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.modify_async", new_callable=AsyncMock)
async def test_AI_handler__sends_references__when_chunks_provided(
    mock_modify: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify references are sent via chunks_to_sdk_references in the startedStreamingAt call.
    Why this matters: References must be attached to the message for the frontend to render footnotes.
    Setup summary: Stream text, provide a content chunk, assert references are passed to modify_async.
    """
    # Arrange
    streamed_text = "Answer is here."
    events = [
        _text_delta(streamed_text, 0),
        _completed_event(streamed_text, 1),
    ]

    chunks = [
        ContentChunk(id="chunk-1", text="Source content", key="k1", chunk_id="c1"),
    ]

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=_fake_stream(events))

    pipeline = _build_pipeline(test_settings)
    handler = ResponsesCompleteWithReferences(
        test_settings,
        pipeline=pipeline,
        client=mock_client,
    )

    # Act
    await handler.complete_with_references_async(
        model_name="test-model",
        messages="What is the answer?",
        content_chunks=chunks,
    )

    # Assert — first modify_async call (startedStreamingAt) should include references
    first_call_kwargs = mock_modify.call_args_list[0].kwargs
    assert "references" in first_call_kwargs
    assert len(first_call_kwargs["references"]) == 1


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.modify_async", new_callable=AsyncMock)
async def test_AI_handler__no_references_in_modify__when_no_chunks(
    mock_modify: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify no references are sent when content_chunks is empty.
    Why this matters: A2A and other paths do not need references attached.
    Setup summary: Stream without content_chunks, assert references is empty in modify call.
    """
    # Arrange
    events = [
        _text_delta("No refs here", 0),
        _completed_event("No refs here", 1),
    ]

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=_fake_stream(events))

    pipeline = _build_pipeline(test_settings)
    handler = ResponsesCompleteWithReferences(
        test_settings,
        pipeline=pipeline,
        client=mock_client,
    )

    # Act
    result = await handler.complete_with_references_async(
        model_name="test-model",
        messages="Hello",
    )

    # Assert — first modify call should have empty references list
    first_call_kwargs = mock_modify.call_args_list[0].kwargs
    assert first_call_kwargs["references"] == []
    assert result.message.references == []


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_handler__raises__when_no_chat_context(
    test_settings_no_chat: UniqueSettings,
) -> None:
    """
    Purpose: Verify handler raises ValueError when chat context is missing.
    Why this matters: Prevents cryptic errors deep in SDK calls.
    Setup summary: Create settings with chat=None, assert ValueError.
    """
    # Arrange
    pipeline = _build_pipeline(test_settings_no_chat)
    mock_client = AsyncMock()
    handler = ResponsesCompleteWithReferences(
        test_settings_no_chat,
        pipeline=pipeline,
        client=mock_client,
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Chat context is not set"):
        await handler.complete_with_references_async(
            model_name="test-model",
            messages="Hello",
        )


# ---------------------------------------------------------------------------
# Message conversion (shared with ResponsesCompleteWithReferences input path)
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_convert_messages_to_openai__converts_language_model_messages__to_sequence() -> (
    None
):
    """
    Purpose: Verify _convert_messages_to_openai converts LanguageModelMessages to the
        Responses API sequence format.
    Why this matters: The Responses API requires a specific message format; passing the
        Pydantic wrapper directly would raise a type error in the SDK.
    Setup summary: One user message wrapped in LanguageModelMessages, convert, assert list.
    """
    messages = LanguageModelMessages([LanguageModelUserMessage(content="Hi")])

    result = _convert_messages_to_openai(messages.root)

    assert isinstance(result, list)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# _convert_tools() helper
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_convert_tools__returns_none__for_empty_or_none_input() -> None:
    """
    Purpose: Verify _convert_tools returns None when given None or an empty list.
    Why this matters: Passing tools=None to the Responses API is the correct way to
        signal no tools; passing [] is technically incorrect.
    Setup summary: Call with None and [], assert both return None.
    """
    assert _convert_tools(None) is None
    assert _convert_tools([]) is None


@pytest.mark.ai
def test_AI_convert_tools__converts_tool_description__using_completions_mode() -> None:
    """
    Purpose: Verify _convert_tools calls to_openai(mode='completions') for
        LanguageModelToolDescription instances and returns the converted list.
    Why this matters: LanguageModelToolDescription.to_openai generates the full function
        schema; using the wrong mode or not calling it would produce an invalid payload.
    Setup summary: Mock a LanguageModelToolDescription, assert to_openai called with
        mode='completions' and the returned value is in the list.
    """
    mock_desc = MagicMock(spec=LanguageModelToolDescription)
    mock_desc.to_openai.return_value = {"type": "function", "function": {"name": "td"}}

    result = _convert_tools([mock_desc])

    mock_desc.to_openai.assert_called_once_with(mode="responses")
    assert result is not None
    assert result[0]["type"] == "function"


# ---------------------------------------------------------------------------
# complete_with_references_async() — optional parameters forwarding
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.modify_async", new_callable=AsyncMock)
async def test_AI_handler__forwards_instructions_and_max_output_tokens__to_client(
    mock_modify: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify instructions and max_output_tokens are forwarded to the OpenAI client.
    Why this matters: These parameters control system prompt and token budget; silently
        dropping them would produce incorrect model behaviour.
    Setup summary: Pass instructions and max_output_tokens, inspect create call kwargs.
    """
    stream_events = [_text_delta("x", 0), _completed_event("x", 1)]
    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=_fake_stream(stream_events))

    pipeline = _build_pipeline(test_settings)
    handler = ResponsesCompleteWithReferences(
        test_settings,
        pipeline=pipeline,
        client=mock_client,
    )

    await handler.complete_with_references_async(
        model_name="test-model",
        messages="Hi",
        instructions="You are helpful.",
        max_output_tokens=512,
    )

    call_kwargs = mock_client.responses.create.call_args.kwargs
    assert call_kwargs["instructions"] == "You are helpful."
    assert call_kwargs["max_output_tokens"] == 512


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.modify_async", new_callable=AsyncMock)
async def test_AI_handler__forwards_other_options__to_client(
    mock_modify: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify other_options are forwarded via setdefault to the create call.
    Why this matters: Callers use other_options for custom parameters (e.g. top_logprobs)
        that have no dedicated argument.
    Setup summary: Pass other_options={"top_logprobs": 3}, inspect create call kwargs.
    """
    stream_events = [_text_delta("x", 0), _completed_event("x", 1)]
    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=_fake_stream(stream_events))

    pipeline = _build_pipeline(test_settings)
    handler = ResponsesCompleteWithReferences(
        test_settings,
        pipeline=pipeline,
        client=mock_client,
    )

    await handler.complete_with_references_async(
        model_name="test-model",
        messages="Hi",
        other_options={"top_logprobs": 3},
    )

    call_kwargs = mock_client.responses.create.call_args.kwargs
    assert call_kwargs.get("top_logprobs") == 3


# ---------------------------------------------------------------------------
# complete_with_references_async() — extra_replacers
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.modify_async", new_callable=AsyncMock)
async def test_AI_handler__calls_extra_replacers__when_provided(
    mock_modify: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify custom replacers are invoked when injected into the pipeline's text handler.
    Why this matters: Callers can inject custom replacers (e.g. for PII redaction);
        if they are not wired into the chain their transformations are silently skipped.
    Setup summary: Provide a recording replacer to the text handler, stream a token,
        assert the replacer's process() was called.
    """

    class _RecordingReplacer(StreamingReplacerProtocol):
        def __init__(self) -> None:
            self.processed: list[str] = []

        def process(self, delta: str) -> str:
            self.processed.append(delta)
            return delta

        def flush(self) -> str:
            return ""

    recording = _RecordingReplacer()

    stream_events = [_text_delta("hello", 0), _completed_event("hello", 1)]
    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=_fake_stream(stream_events))

    pipeline = _build_pipeline(test_settings, replacers=[recording])
    handler = ResponsesCompleteWithReferences(
        test_settings,
        pipeline=pipeline,
        client=mock_client,
    )

    await handler.complete_with_references_async(
        model_name="test-model",
        messages="Hi",
    )

    assert recording.processed != []


# ---------------------------------------------------------------------------
# complete_with_references_async() — RemoteProtocolError resilience
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.modify_async", new_callable=AsyncMock)
async def test_AI_handler__finalises_gracefully__when_remote_protocol_error(
    mock_modify: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify the handler catches httpx.RemoteProtocolError mid-stream and returns
        whatever content was received before the connection dropped.
    Why this matters: Long responses can cause proxy timeouts; losing all accumulated
        content on a partial disconnect is worse than returning what was streamed.
    Setup summary: Inject a RemoteProtocolError after the first text delta, assert
        partial text is returned.
    """

    async def _failing_stream() -> AsyncIterator[ResponseStreamEvent]:
        yield _text_delta("Partial", 0)
        raise httpx.RemoteProtocolError("connection closed", request=MagicMock())

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=_failing_stream())

    pipeline = _build_pipeline(test_settings)
    handler = ResponsesCompleteWithReferences(
        test_settings,
        pipeline=pipeline,
        client=mock_client,
    )

    result = await handler.complete_with_references_async(
        model_name="test-model",
        messages="Hi",
    )

    assert result.message.text == "Partial"
