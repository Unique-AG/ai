"""Tests for ChatCompletionsCompleteWithReferences and helper functions."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from openai.types.chat.chat_completion_chunk import (
    ChatCompletionChunk,
    Choice,
    ChoiceDelta,
    ChoiceDeltaToolCall,
    ChoiceDeltaToolCallFunction,
)

from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    NORMALIZATION_MAX_MATCH_LENGTH,
    NORMALIZATION_PATTERNS,
    StreamingPatternReplacer,
    StreamingReplacerProtocol,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completions.complete_with_references import (
    ChatCompletionsCompleteWithReferences,
    _convert_messages,
    _convert_tools,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completions.stream_pipeline import (
    ChatCompletionStreamPipeline,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completions.text_handler import (
    ChatCompletionTextHandler,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completions.tool_call_handler import (
    ChatCompletionToolCallHandler,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelStreamResponse,
    LanguageModelTool,
    LanguageModelToolDescription,
    LanguageModelToolParameters,
    LanguageModelUserMessage,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _build_pipeline(
    settings: UniqueSettings,
    *,
    replacers: list[StreamingReplacerProtocol] | None = None,
) -> ChatCompletionStreamPipeline:
    r = replacers
    if r is None:
        r = [
            StreamingPatternReplacer(
                replacements=NORMALIZATION_PATTERNS,
                max_match_length=NORMALIZATION_MAX_MATCH_LENGTH,
            )
        ]
    return ChatCompletionStreamPipeline(
        text_handler=ChatCompletionTextHandler(settings=settings, replacers=r),
        tool_call_handler=ChatCompletionToolCallHandler(),
    )


def _text_chunk(
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
        model="test-model",
        object="chat.completion.chunk",
    )


def _tool_chunk(
    index: int,
    call_id: str | None = None,
    name: str | None = None,
    arguments: str | None = None,
    finish_reason: str | None = None,
) -> ChatCompletionChunk:
    return ChatCompletionChunk.model_construct(
        id="c-tc",
        choices=[
            Choice.model_construct(
                delta=ChoiceDelta.model_construct(
                    content=None,
                    tool_calls=[
                        ChoiceDeltaToolCall.model_construct(
                            index=index,
                            id=call_id,
                            function=ChoiceDeltaToolCallFunction.model_construct(
                                name=name,
                                arguments=arguments,
                            ),
                            type="function",
                        )
                    ],
                ),
                finish_reason=finish_reason,
                index=0,
            )
        ],
        created=0,
        model="test-model",
        object="chat.completion.chunk",
    )


async def _fake_stream(
    chunks: list[ChatCompletionChunk],
) -> AsyncIterator[ChatCompletionChunk]:
    for chunk in chunks:
        yield chunk


# ---------------------------------------------------------------------------
# _convert_messages()
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_convert_messages__serialises_language_model_messages__to_list_of_dicts() -> (
    None
):
    """
    Purpose: Verify _convert_messages converts LanguageModelMessages to the plain-dict
        format that the OpenAI SDK expects.
    Why this matters: The Chat Completions API requires a list of dicts, not Pydantic
        objects; passing the wrong type raises a validation error.
    Setup summary: Wrap one user message, convert, assert list with role/content keys.
    """
    messages = LanguageModelMessages([LanguageModelUserMessage(content="Hello")])

    result = _convert_messages(messages)

    assert isinstance(result, list)
    assert result[0]["role"] == "user"
    assert result[0]["content"] == "Hello"


@pytest.mark.ai
def test_AI_convert_messages__returns_list_unchanged__when_already_dicts() -> None:
    """
    Purpose: Verify _convert_messages passes through a raw list of dicts unchanged.
    Why this matters: Some callers already hold pre-serialised messages; adding a
        conversion step should be a no-op for them.
    Setup summary: Pass a list with one dict, assert the same list is returned.
    """
    raw: list = [{"role": "user", "content": "Hi"}]

    result = _convert_messages(raw)

    assert result == raw


# ---------------------------------------------------------------------------
# _convert_tools()
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_convert_tools__returns_none__when_tools_is_none() -> None:
    """
    Purpose: Verify _convert_tools returns None for empty / missing tool lists.
    Why this matters: Passing tools=None to the OpenAI API is the correct way to
        indicate no tools; passing [] would be ignored but is less explicit.
    Setup summary: Pass None and empty list, assert None returned for both.
    """
    assert _convert_tools(None) is None
    assert _convert_tools([]) is None


@pytest.mark.ai
def test_AI_convert_tools__serialises_language_model_tool__to_openai_function_dict() -> (
    None
):
    """
    Purpose: Verify _convert_tools converts LanguageModelTool into the dict format
        that the Chat Completions API expects.
    Why this matters: A wrongly structured tool dict raises a 400 from the API.
    Setup summary: One LanguageModelTool, convert, assert outer 'type'='function' key.
    """
    tool = LanguageModelTool(
        name="my_fn",
        description="does something",
        parameters=LanguageModelToolParameters(properties={}, required=[]),
    )

    result = _convert_tools([tool])

    assert result is not None
    assert result[0]["type"] == "function"
    assert result[0]["function"]["name"] == "my_fn"


@pytest.mark.ai
def test_AI_convert_tools__converts_tool_description__using_completions_mode() -> None:
    """
    Purpose: Verify _convert_tools calls to_openai(mode='completions') for
        LanguageModelToolDescription instances.
    Why this matters: LanguageModelToolDescription.to_openai generates the full
        function schema; using the wrong mode would produce an invalid payload.
    Setup summary: Mock a LanguageModelToolDescription, assert to_openai called with
        mode='completions'.
    """
    mock_desc = MagicMock(spec=LanguageModelToolDescription)
    mock_desc.to_openai.return_value = {"type": "function", "function": {"name": "td"}}

    result = _convert_tools([mock_desc])

    mock_desc.to_openai.assert_called_once_with(mode="completions")
    assert result is not None
    assert result[0]["function"]["name"] == "td"


# ---------------------------------------------------------------------------
# complete_with_references_async() — validation
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_handler__raises_value_error__when_chat_context_is_none(
    test_settings_no_chat: UniqueSettings,
) -> None:
    """
    Purpose: Verify the handler raises ValueError early when chat context is missing.
    Why this matters: Prevents cryptic errors deep in SDK or accumulator calls.
    Setup summary: Settings with chat=None, call complete_with_references_async, assert ValueError.
    """
    handler = ChatCompletionsCompleteWithReferences(
        test_settings_no_chat,
        pipeline=_build_pipeline(test_settings_no_chat),
    )

    with pytest.raises(ValueError, match="Chat context is not set"):
        await handler.complete_with_references_async(
            messages=LanguageModelMessages([LanguageModelUserMessage(content="Hi")]),
            model_name="test-model",
        )


# ---------------------------------------------------------------------------
# complete_with_references_async() — happy path
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.modify_async", new_callable=AsyncMock)
async def test_AI_handler__streams_text_and_returns_result__happy_path(
    mock_modify: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify the handler streams text chunks and returns a LanguageModelStreamResponse
        with the accumulated text and usage.
    Why this matters: Core contract for pipeline-backed Chat Completions streaming.
    Setup summary: Two text chunks + stop chunk, mock SDK calls, assert result text.
    """
    chunks = [
        _text_chunk("Hello"),
        _text_chunk(" world"),
        _text_chunk(None, finish_reason="stop"),
    ]
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=_fake_stream(chunks))

    handler = ChatCompletionsCompleteWithReferences(
        test_settings,
        pipeline=_build_pipeline(test_settings),
        client=mock_client,
    )

    result = await handler.complete_with_references_async(
        messages=LanguageModelMessages([LanguageModelUserMessage(content="Q")]),
        model_name="test-model",
    )

    assert isinstance(result, LanguageModelStreamResponse)
    assert result.message.text == "Hello world"
    assert mock_modify.await_count >= 1


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.modify_async", new_callable=AsyncMock)
async def test_AI_handler__sends_references__when_content_chunks_provided(
    mock_modify: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify references are sent via chunks_to_sdk_references in the startedStreamingAt call.
    Why this matters: References must be attached to the message for the frontend to render footnotes.
    Setup summary: Stream text, provide a content chunk, assert references are passed to modify_async.
    """
    text = "Answer here."
    stream_chunks = [_text_chunk(text), _text_chunk(None, finish_reason="stop")]
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_fake_stream(stream_chunks)
    )

    content_chunks = [ContentChunk(id="ch1", chunk_id="c1", key="k1", title="Src 1")]
    handler = ChatCompletionsCompleteWithReferences(
        test_settings,
        pipeline=_build_pipeline(test_settings),
        client=mock_client,
    )

    await handler.complete_with_references_async(
        messages=LanguageModelMessages([LanguageModelUserMessage(content="Q")]),
        model_name="test-model",
        content_chunks=content_chunks,
    )

    first_call_kwargs = mock_modify.call_args_list[0].kwargs
    assert "references" in first_call_kwargs
    assert len(first_call_kwargs["references"]) == 1


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.modify_async", new_callable=AsyncMock)
async def test_AI_handler__message_references_empty__when_pipeline_has_pattern_replacers_only(
    mock_modify: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify result message references stay empty when only normalisation replacers run.
    Why this matters: Pattern replacers do not attach structured ContentReference objects;
        the streamed toolkit response therefore has empty message references unless another
        path (e.g. Integrated) resolves them.
    Setup summary: Default pipeline (pattern replacer only) with chunks provided.
    """
    text = "No refs."
    stream_chunks = [_text_chunk(text), _text_chunk(None, finish_reason="stop")]
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_fake_stream(stream_chunks)
    )

    content_chunks = [ContentChunk(id="ch1", chunk_id="c1", key="k1")]
    handler = ChatCompletionsCompleteWithReferences(
        test_settings,
        pipeline=_build_pipeline(test_settings),
        client=mock_client,
    )

    result = await handler.complete_with_references_async(
        messages=LanguageModelMessages([LanguageModelUserMessage(content="Q")]),
        model_name="test-model",
        content_chunks=content_chunks,
    )

    assert result.message.references == []


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
    stream_chunks = [
        _text_chunk("No sources."),
        _text_chunk(None, finish_reason="stop"),
    ]
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_fake_stream(stream_chunks)
    )

    handler = ChatCompletionsCompleteWithReferences(
        test_settings,
        pipeline=_build_pipeline(test_settings),
        client=mock_client,
    )

    result = await handler.complete_with_references_async(
        messages=LanguageModelMessages([LanguageModelUserMessage(content="Q")]),
        model_name="test-model",
    )

    first_call_kwargs = mock_modify.call_args_list[0].kwargs
    assert first_call_kwargs["references"] == []
    assert result.message.references == []


# ---------------------------------------------------------------------------
# complete_with_references_async() — tool calls
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.modify_async", new_callable=AsyncMock)
async def test_AI_handler__returns_tool_calls__when_model_emits_function_call(
    mock_modify: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify the handler assembles tool calls from chunk deltas and returns them
        in result.tool_calls.
    Why this matters: Agentic loops depend on tool_calls to dispatch function execution;
        a missing or malformed tool call breaks the loop.
    Setup summary: Stream name + arguments chunks for one tool call, assert result.tool_calls.
    """
    stream_chunks = [
        _tool_chunk(0, call_id="tc-1", name="get_weather"),
        _tool_chunk(0, arguments='{"city":'),
        _tool_chunk(0, arguments='"Paris"}', finish_reason="tool_calls"),
    ]
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_fake_stream(stream_chunks)
    )

    handler = ChatCompletionsCompleteWithReferences(
        test_settings,
        pipeline=_build_pipeline(test_settings),
        client=mock_client,
    )

    result = await handler.complete_with_references_async(
        messages=LanguageModelMessages([LanguageModelUserMessage(content="Weather?")]),
        model_name="test-model",
    )

    assert result.tool_calls is not None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "get_weather"
    assert result.tool_calls[0].arguments == {"city": "Paris"}


# ---------------------------------------------------------------------------
# complete_with_references_async() — error resilience
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
    Why this matters: Long responses can cause proxy timeouts; losing all content on a
        partial disconnect is worse than returning what was streamed.
    Setup summary: Inject a RemoteProtocolError after the first chunk, assert partial text returned.
    """

    async def _failing_stream() -> AsyncIterator[ChatCompletionChunk]:
        yield _text_chunk("Partial")
        raise httpx.RemoteProtocolError("connection closed", request=MagicMock())

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=_failing_stream())

    handler = ChatCompletionsCompleteWithReferences(
        test_settings,
        pipeline=_build_pipeline(test_settings),
        client=mock_client,
    )

    result = await handler.complete_with_references_async(
        messages=LanguageModelMessages([LanguageModelUserMessage(content="Q")]),
        model_name="test-model",
    )

    assert result.message.text == "Partial"


# ---------------------------------------------------------------------------
# complete_with_references_async() — other_options / extra config
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.modify_async", new_callable=AsyncMock)
async def test_AI_handler__passes_other_options__to_openai_client(
    mock_modify: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify other_options are forwarded to the OpenAI client create call.
    Why this matters: Callers use other_options for custom parameters like max_tokens
        or response_format that have no dedicated argument.
    Setup summary: Pass other_options={"max_tokens": 10}, inspect create call kwargs.
    """
    stream_chunks = [_text_chunk("x"), _text_chunk(None, finish_reason="stop")]
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_fake_stream(stream_chunks)
    )

    handler = ChatCompletionsCompleteWithReferences(
        test_settings,
        pipeline=_build_pipeline(test_settings),
        client=mock_client,
    )

    await handler.complete_with_references_async(
        messages=LanguageModelMessages([LanguageModelUserMessage(content="Q")]),
        model_name="test-model",
        other_options={"max_tokens": 10},
    )

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs.get("max_tokens") == 10


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.modify_async", new_callable=AsyncMock)
async def test_AI_handler__disables_normalization__when_no_replacers_configured(
    mock_modify: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify an empty replacer list disables citation normalisation.
    Why this matters: A2A and other non-RAG paths must not have their text modified by
        citation normalisation.
    Setup summary: Build pipeline with replacers=[], stream text with [source 1], assert
        text is unchanged (no StreamingPatternReplacer).
    """
    text = "[source 1] is preserved."
    stream_chunks = [_text_chunk(text), _text_chunk(None, finish_reason="stop")]
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_fake_stream(stream_chunks)
    )

    handler = ChatCompletionsCompleteWithReferences(
        test_settings,
        pipeline=_build_pipeline(test_settings, replacers=[]),
        client=mock_client,
    )

    result = await handler.complete_with_references_async(
        messages=LanguageModelMessages([LanguageModelUserMessage(content="Q")]),
        model_name="test-model",
    )

    assert result.message.text == text
