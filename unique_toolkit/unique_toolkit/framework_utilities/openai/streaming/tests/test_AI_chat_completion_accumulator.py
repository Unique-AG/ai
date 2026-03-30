"""Tests for ChatCompletionStreamAccumulator and iter_chat_completion_chunks_until_tool_calls."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone

import pytest
from openai.types.chat.chat_completion_chunk import (
    ChatCompletionChunk,
    Choice,
    ChoiceDelta,
    ChoiceDeltaToolCall,
    ChoiceDeltaToolCallFunction,
)

from unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completion_accumulator import (
    ChatCompletionStreamAccumulator,
    iter_chat_completion_chunks_until_tool_calls,
)
from unique_toolkit.language_model.schemas import LanguageModelStreamResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _text_chunk(
    content: str | None, finish_reason: str | None = None
) -> ChatCompletionChunk:
    return ChatCompletionChunk.model_construct(
        id="chunk-1",
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
) -> ChatCompletionChunk:
    return ChatCompletionChunk.model_construct(
        id="chunk-tc",
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
                finish_reason=None,
                index=0,
            )
        ],
        created=0,
        model="test-model",
        object="chat.completion.chunk",
    )


def _empty_choices_chunk() -> ChatCompletionChunk:
    return ChatCompletionChunk.model_construct(
        id="chunk-empty",
        choices=[],
        created=0,
        model="test-model",
        object="chat.completion.chunk",
    )


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_reset__clears_full_text_and_tool_calls__after_accumulation() -> None:
    """
    Purpose: Verify reset() erases all accumulated state.
    Why this matters: Sequential reuse of the accumulator must not carry stale data
        from a prior stream into the next request.
    Setup summary: Accumulate text and a tool call, reset, assert empty state.
    """
    acc = ChatCompletionStreamAccumulator()
    acc.apply(_text_chunk("Hello"))
    acc.apply(_tool_chunk(0, call_id="c1", name="fn", arguments='{"x":1}'))

    acc.reset()

    assert acc.full_text == ""
    assert acc.chat_completion_tool_calls() == []


# ---------------------------------------------------------------------------
# apply() — text
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_apply__accumulates_text_deltas__across_multiple_chunks() -> None:
    """
    Purpose: Verify apply() concatenates content from successive chunks into full_text.
    Why this matters: The assistant message shown to the user is built from all deltas;
        a missed delta leaves the text incomplete.
    Setup summary: Two text chunks, apply both, assert concatenated full_text.
    """
    acc = ChatCompletionStreamAccumulator()
    acc.apply(_text_chunk("Hello"))
    acc.apply(_text_chunk(" world"))

    assert acc.full_text == "Hello world"


@pytest.mark.ai
def test_AI_apply__ignores_chunk__when_choices_is_empty() -> None:
    """
    Purpose: Verify apply() is a no-op when the chunk has no choices.
    Why this matters: OpenAI streams occasionally emit usage-only chunks with empty choices;
        these must not crash or corrupt state.
    Setup summary: Apply an empty-choices chunk, assert full_text remains empty.
    """
    acc = ChatCompletionStreamAccumulator()
    acc.apply(_empty_choices_chunk())

    assert acc.full_text == ""


@pytest.mark.ai
def test_AI_apply__skips_null_content__without_adding_to_text() -> None:
    """
    Purpose: Verify apply() does not append anything when delta.content is None.
    Why this matters: Tool-call chunks typically have content=None; treating None as ""
        is correct, but the accumulator must not add the literal string "None".
    Setup summary: Apply a chunk with content=None, assert full_text unchanged.
    """
    acc = ChatCompletionStreamAccumulator()
    acc.apply(_text_chunk(None))

    assert acc.full_text == ""


# ---------------------------------------------------------------------------
# apply() — tool calls
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_apply__creates_tool_call_entry__on_first_chunk_for_index() -> None:
    """
    Purpose: Verify apply() initialises a tool call slot when it sees a new index.
    Why this matters: Tool call assembly is index-keyed; missing an initialisation
        would cause a KeyError or silently drop arguments on later chunks.
    Setup summary: Apply a single tool-call delta, assert one tool call is tracked.
    """
    acc = ChatCompletionStreamAccumulator()
    acc.apply(_tool_chunk(0, call_id="call-1", name="my_fn", arguments='{"a":'))

    calls = acc.chat_completion_tool_calls()
    assert len(calls) == 1
    assert calls[0].id == "call-1"
    assert calls[0].function.name == "my_fn"
    assert calls[0].function.arguments == '{"a":'


@pytest.mark.ai
def test_AI_apply__appends_arguments__across_incremental_chunks() -> None:
    """
    Purpose: Verify apply() concatenates function.arguments from successive chunks.
    Why this matters: JSON arguments arrive token-by-token; only concatenation
        produces a parseable string for build_stream_result.
    Setup summary: Three argument fragments applied in sequence, assert joined result.
    """
    acc = ChatCompletionStreamAccumulator()
    acc.apply(_tool_chunk(0, call_id="c1", name="fn"))
    acc.apply(_tool_chunk(0, arguments='{"x":'))
    acc.apply(_tool_chunk(0, arguments="1}"))

    calls = acc.chat_completion_tool_calls()
    assert calls[0].function.arguments == '{"x":1}'


@pytest.mark.ai
def test_AI_apply__handles_multiple_tool_calls__by_index() -> None:
    """
    Purpose: Verify apply() tracks independent tool calls at different indices.
    Why this matters: Parallel tool calls use separate indices; merging them would
        corrupt both calls.
    Setup summary: Two tool calls at index 0 and 1, assert both present with correct names.
    """
    acc = ChatCompletionStreamAccumulator()
    acc.apply(_tool_chunk(0, call_id="c1", name="fn_a", arguments="{}"))
    acc.apply(_tool_chunk(1, call_id="c2", name="fn_b", arguments="{}"))

    calls = acc.chat_completion_tool_calls()
    assert len(calls) == 2
    assert calls[0].function.name == "fn_a"
    assert calls[1].function.name == "fn_b"


# ---------------------------------------------------------------------------
# build_stream_result() — text only
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_build_stream_result__returns_response_with_message_text__no_tool_calls() -> (
    None
):
    """
    Purpose: Verify build_stream_result() returns a valid LanguageModelStreamResponse
        with the accumulated text and no tool_calls for a plain text stream.
    Why this matters: The downstream handler and tests depend on result.message.text
        and result.tool_calls being set correctly.
    Setup summary: Accumulate two text deltas, build result, assert text and null tool_calls.
    """
    acc = ChatCompletionStreamAccumulator()
    acc.apply(_text_chunk("Hello"))
    acc.apply(_text_chunk(" world"))

    result = acc.build_stream_result(
        message_id="msg-1", chat_id="chat-1", created_at=_TS
    )

    assert isinstance(result, LanguageModelStreamResponse)
    assert result.message.text == "Hello world"
    assert result.tool_calls is None


@pytest.mark.ai
def test_AI_build_stream_result__sets_message_id_and_chat_id__from_kwargs() -> None:
    """
    Purpose: Verify the message object carries the IDs passed to build_stream_result.
    Why this matters: The persistence layer uses message_id to correlate events;
        a wrong ID would break message threading.
    Setup summary: Call build_stream_result with known IDs, assert they appear on message.
    """
    acc = ChatCompletionStreamAccumulator()
    acc.apply(_text_chunk("x"))

    result = acc.build_stream_result(
        message_id="my-msg", chat_id="my-chat", created_at=_TS
    )

    assert result.message.id == "my-msg"
    assert result.message.chat_id == "my-chat"


# ---------------------------------------------------------------------------
# build_stream_result() — tool call argument parsing
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_build_stream_result__parses_json_arguments__into_dict() -> None:
    """
    Purpose: Verify build_stream_result parses valid JSON arguments into a dict.
    Why this matters: Callers execute tool calls by reading LanguageModelFunction.arguments
        as a dict; unparsed strings would break every downstream tool dispatch.
    Setup summary: Accumulate a complete JSON argument string, build result, assert dict.
    """
    acc = ChatCompletionStreamAccumulator()
    acc.apply(_tool_chunk(0, call_id="c1", name="add", arguments='{"a": 1, "b": 2}'))

    result = acc.build_stream_result(
        message_id="msg-1", chat_id="chat-1", created_at=_TS
    )

    assert result.tool_calls is not None
    assert result.tool_calls[0].arguments == {"a": 1, "b": 2}


@pytest.mark.ai
def test_AI_build_stream_result__sets_arguments_none__when_empty_string() -> None:
    """
    Purpose: Verify build_stream_result sets arguments=None when the accumulated
        argument string is empty (no arguments streamed).
    Why this matters: Tool calls with no arguments (e.g. 'get_time()') must not
        crash the JSON parser.
    Setup summary: Tool chunk with empty arguments, build result, assert arguments is None.
    """
    acc = ChatCompletionStreamAccumulator()
    acc.apply(_tool_chunk(0, call_id="c1", name="fn", arguments=""))

    result = acc.build_stream_result(
        message_id="msg-1", chat_id="chat-1", created_at=_TS
    )

    assert result.tool_calls is not None
    assert result.tool_calls[0].arguments is None


@pytest.mark.ai
def test_AI_build_stream_result__sets_arguments_none__when_json_invalid(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Purpose: Verify build_stream_result handles malformed JSON gracefully by setting
        arguments=None and logging a warning.
    Why this matters: A hard crash on bad JSON would kill the entire response; degraded
        handling (no arguments + warning log) is safer.
    Setup summary: Apply invalid JSON arguments, build result, assert None and warning logged.
    """
    acc = ChatCompletionStreamAccumulator()
    acc.apply(_tool_chunk(0, call_id="c1", name="fn", arguments="{bad json"))

    with caplog.at_level("WARNING"):
        result = acc.build_stream_result(
            message_id="msg-1", chat_id="chat-1", created_at=_TS
        )

    assert result.tool_calls is not None
    assert result.tool_calls[0].arguments is None
    assert "JSON decode failed" in caplog.text


@pytest.mark.ai
def test_AI_build_stream_result__wraps_non_dict_json__in_underscore_key() -> None:
    """
    Purpose: Verify build_stream_result wraps a non-dict JSON value (e.g. a list)
        in {"_": value} rather than raising.
    Why this matters: Some models occasionally produce array-valued arguments;
        callers reading arguments["_"] can inspect the raw value.
    Setup summary: Apply a JSON array string, build result, assert wrapped dict.
    """
    acc = ChatCompletionStreamAccumulator()
    acc.apply(_tool_chunk(0, call_id="c1", name="fn", arguments="[1, 2, 3]"))

    result = acc.build_stream_result(
        message_id="msg-1", chat_id="chat-1", created_at=_TS
    )

    assert result.tool_calls is not None
    assert result.tool_calls[0].arguments == {"_": [1, 2, 3]}


# ---------------------------------------------------------------------------
# iter_chat_completion_chunks_until_tool_calls
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_iter_chunks_until_tool_calls__stops_after_tool_calls_finish_reason() -> (
    None
):
    """
    Purpose: Verify the iterator stops yielding after a chunk with finish_reason='tool_calls'.
    Why this matters: Legacy callers using the early-termination helper must not process
        chunks that arrive after the model finishes its tool call.
    Setup summary: Three chunks — text, tool_calls-finished, text — assert only first two yielded.
    """

    async def _source() -> AsyncIterator[ChatCompletionChunk]:
        yield _text_chunk("before")
        yield _text_chunk("done", finish_reason="tool_calls")
        yield _text_chunk("after")  # should never be yielded

    collected = [
        chunk async for chunk in iter_chat_completion_chunks_until_tool_calls(_source())
    ]

    assert len(collected) == 2
    assert collected[0].choices[0].delta.content == "before"
    assert collected[1].choices[0].finish_reason == "tool_calls"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_iter_chunks_until_tool_calls__yields_all_chunks__when_no_tool_calls() -> (
    None
):
    """
    Purpose: Verify the iterator yields every chunk when no tool_calls finish_reason appears.
    Why this matters: Plain text streams must not be terminated early.
    Setup summary: Two text chunks with no tool_calls finish, assert all yielded.
    """

    async def _source() -> AsyncIterator[ChatCompletionChunk]:
        yield _text_chunk("Hello")
        yield _text_chunk(" world", finish_reason="stop")

    collected = [
        chunk async for chunk in iter_chat_completion_chunks_until_tool_calls(_source())
    ]

    assert len(collected) == 2
