"""Tests for ResponsesStreamAccumulator and its private helper functions."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from openai.types.responses import (
    Response,
    ResponseCompletedEvent,
    ResponseFunctionCallArgumentsDoneEvent,
    ResponseOutputItemAddedEvent,
    ResponseTextDeltaEvent,
)
from openai.types.responses.response_function_tool_call_item import (
    ResponseFunctionToolCallItem,
)
from openai.types.responses.response_usage import (
    InputTokensDetails,
    OutputTokensDetails,
    ResponseUsage,
)

from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses_accumulator import (
    ResponsesStreamAccumulator,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelStreamResponse,
    ResponsesLanguageModelStreamResponse,
)

_TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _text_delta(delta: str, seq: int = 0) -> ResponseTextDeltaEvent:
    return ResponseTextDeltaEvent(
        content_index=0,
        delta=delta,
        item_id="msg-1",
        logprobs=[],
        output_index=0,
        sequence_number=seq,
        type="response.output_text.delta",
    )


def _function_added(item_id: str, name: str) -> ResponseOutputItemAddedEvent:
    return ResponseOutputItemAddedEvent(
        item=ResponseFunctionToolCallItem(
            id=item_id,
            call_id=item_id,
            name=name,
            arguments="{}",
            type="function_call",
        ),
        output_index=0,
        sequence_number=0,
        type="response.output_item.added",
    )


def _arguments_done_no_name(
    item_id: str, arguments: str
) -> ResponseFunctionCallArgumentsDoneEvent:
    """Build an arguments-done event without the 'name' field.

    Uses model_construct to simulate older OpenAI SDK versions that omit 'name'
    on ResponseFunctionCallArgumentsDoneEvent, triggering the name-lookup fallback.
    """
    return ResponseFunctionCallArgumentsDoneEvent.model_construct(
        arguments=arguments,
        item_id=item_id,
        output_index=0,
        sequence_number=1,
        type="response.function_call_arguments.done",
    )


def _completed(usage: ResponseUsage | None = None) -> ResponseCompletedEvent:
    response = Response.model_construct(usage=usage, output=None)
    return ResponseCompletedEvent.model_construct(
        response=response,
        sequence_number=99,
        type="response.completed",
    )


def _usage(total: int = 30) -> ResponseUsage:
    return ResponseUsage(
        input_tokens=10,
        input_tokens_details=InputTokensDetails(cached_tokens=0),
        output_tokens=20,
        output_tokens_details=OutputTokensDetails(reasoning_tokens=0),
        total_tokens=total,
    )


# ---------------------------------------------------------------------------
# Properties: aggregated_text, tool_calls, usage
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_aggregated_text_property__returns_current_folded_text() -> None:
    """
    Purpose: Verify aggregated_text reflects the running concatenation of all text deltas.
    Why this matters: SDK persistence reads this property for live streaming preview.
    Setup summary: Apply two deltas, assert property value equals their concatenation.
    """
    acc = ResponsesStreamAccumulator()
    acc.apply(_text_delta("Hello"))
    acc.apply(_text_delta(" world", seq=1))

    assert acc.aggregated_text == "Hello world"


@pytest.mark.ai
def test_AI_tool_calls_property__returns_defensive_copy() -> None:
    """
    Purpose: Verify tool_calls returns a copy so external mutations cannot corrupt state.
    Why this matters: Returning the internal list directly allows callers to silently
        corrupt the accumulator without resetting it.
    Setup summary: Add one tool call, retrieve the list, clear it, assert original intact.
    """
    acc = ResponsesStreamAccumulator()
    acc.apply(_function_added("c1", "fn"))
    acc.apply(
        ResponseFunctionCallArgumentsDoneEvent(
            arguments='{"x": 1}',
            item_id="c1",
            output_index=0,
            sequence_number=1,
            type="response.function_call_arguments.done",
        )
    )

    first = acc.tool_calls
    first.clear()

    assert len(acc.tool_calls) == 1


@pytest.mark.ai
def test_AI_usage_property__is_none_before_completed_event() -> None:
    """
    Purpose: Verify usage is None until a ResponseCompletedEvent arrives.
    Why this matters: Callers must guard against None usage on partial or tool-only streams.
    Setup summary: No events applied, assert usage is None.
    """
    acc = ResponsesStreamAccumulator()

    assert acc.usage is None


@pytest.mark.ai
def test_AI_usage_property__returns_token_counts_after_completed_event() -> None:
    """
    Purpose: Verify usage is populated from the completed event's response.usage.
    Why this matters: Usage data drives quota monitoring and cost attribution.
    Setup summary: Apply completed event with known usage, assert all token counts.
    """
    acc = ResponsesStreamAccumulator()
    acc.apply(_completed(usage=_usage(total=30)))

    assert acc.usage is not None
    assert acc.usage.prompt_tokens == 10
    assert acc.usage.completion_tokens == 20
    assert acc.usage.total_tokens == 30


@pytest.mark.ai
def test_AI_usage_property__returns_none__when_completed_event_has_no_usage() -> None:
    """
    Purpose: Verify usage stays None when the completed event carries no usage object.
    Why this matters: Streaming completions may omit usage; callers must not crash on None.
    Setup summary: Apply completed event with usage=None, assert acc.usage is None.
    """
    acc = ResponsesStreamAccumulator()
    acc.apply(_completed(usage=None))

    assert acc.usage is None


# ---------------------------------------------------------------------------
# build_language_model_stream_response (descriptive alias)
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_build_language_model_stream_response__returns_same_type_as_build_stream_result() -> (
    None
):
    """
    Purpose: Verify the descriptive alias produces an identical LanguageModelStreamResponse.
    Why this matters: Responses callers may use this alias; it must behave identically to
        build_stream_result to avoid surprising divergence.
    Setup summary: Apply a text delta, call alias, assert type and text.
    """
    acc = ResponsesStreamAccumulator()
    acc.apply(_text_delta("hi"))

    result = acc.build_language_model_stream_response(
        message_id="msg-1", chat_id="chat-1", created_at=_TS
    )

    assert isinstance(result, LanguageModelStreamResponse)
    assert result.message.text == "hi"


# ---------------------------------------------------------------------------
# build_responses_stream_result
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_build_responses_stream_result__returns_responses_type_with_output() -> None:
    """
    Purpose: Verify build_responses_stream_result returns ResponsesLanguageModelStreamResponse.
    Why this matters: The Responses-specific type carries the output list; callers that
        need code-interpreter results or file outputs depend on this method.
    Setup summary: Apply a text delta, call build_responses_stream_result, assert type.
    """
    acc = ResponsesStreamAccumulator()
    acc.apply(_text_delta("content"))

    result = acc.build_responses_stream_result(
        message_id="msg-1", chat_id="chat-1", created_at=_TS
    )

    assert isinstance(result, ResponsesLanguageModelStreamResponse)
    assert result.message.text == "content"


@pytest.mark.ai
def test_AI_build_responses_stream_result__raises__on_double_build() -> None:
    """
    Purpose: Verify calling build_responses_stream_result twice raises RuntimeError.
    Why this matters: The finalized guard prevents emitting two responses from one fold,
        which would produce duplicate messages in the Unique platform.
    Setup summary: Call build_responses_stream_result twice, assert RuntimeError on second call.
    """
    acc = ResponsesStreamAccumulator()
    acc.apply(_text_delta("x"))
    acc.build_responses_stream_result(
        message_id="msg-1", chat_id="chat-1", created_at=_TS
    )

    with pytest.raises(RuntimeError, match="already produced a result"):
        acc.build_responses_stream_result(
            message_id="msg-1", chat_id="chat-1", created_at=_TS
        )


# ---------------------------------------------------------------------------
# Tool name resolution fallback
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_function_call__resolves_name_from_output_item__when_event_lacks_name() -> (
    None
):
    """
    Purpose: Verify tool name falls back to the OutputItemAdded event when
        ResponseFunctionCallArgumentsDoneEvent has no 'name' attribute.
    Why this matters: Older OpenAI SDK versions omit 'name' on arguments-done events;
        without the fallback the resolved tool call has an empty name breaking dispatch.
    Setup summary: Register name via OutputItemAdded, apply arguments-done without 'name'
        field (via model_construct), assert tool_call.name matches the registered name.
    """
    acc = ResponsesStreamAccumulator()
    acc.apply(_function_added("call_1", "my_tool"))
    acc.apply(_arguments_done_no_name("call_1", '{"k": "v"}'))

    calls = acc.tool_calls
    assert calls[0].name == "my_tool"


# ---------------------------------------------------------------------------
# JSON decode edge cases in _language_model_function_from_arguments_done
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_apply__logs_warning_and_sets_none_args__when_arguments_are_invalid_json(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Purpose: Verify that invalid JSON in function arguments produces None and logs a warning.
    Why this matters: A model can emit malformed JSON; the pipeline must not crash and should
        surface a diagnostic rather than silently dropping the call.
    Setup summary: Apply arguments-done with bad JSON string, assert arguments is None
        and a WARNING containing 'JSON decode failed' is present.
    """
    acc = ResponsesStreamAccumulator()
    acc.apply(_function_added("c1", "fn"))
    with caplog.at_level("WARNING"):
        acc.apply(
            ResponseFunctionCallArgumentsDoneEvent(
                arguments="{bad json",
                item_id="c1",
                output_index=0,
                sequence_number=1,
                type="response.function_call_arguments.done",
            )
        )

    assert acc.tool_calls[0].arguments is None
    assert "JSON decode failed" in caplog.text
