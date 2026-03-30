"""Tests for Responses API streaming pipeline (accumulator + runner)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from datetime import datetime, timezone

import pytest
from openai.types.responses import (
    Response,
    ResponseCompletedEvent,
    ResponseFunctionCallArgumentsDoneEvent,
    ResponseOutputItemAddedEvent,
    ResponseStreamEvent,
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

from unique_toolkit.framework_utilities.openai.streaming.pipeline import (
    ResponsesStreamAccumulator,
    run_responses_stream_pipeline,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.protocols import (
    ResponseStreamPersistenceProtocol,
)


async def _responses_events_to_stream(
    events: Sequence[ResponseStreamEvent],
) -> AsyncIterator[ResponseStreamEvent]:
    for e in events:
        yield e


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_run_responses_stream_pipeline_accumulates_text_and_usage() -> None:
    """
    Purpose: Verify text deltas and completed usage fold into LanguageModelStreamResponse.
    Why this matters: Core contract for OpenAI/LiteLLM Responses streams.
    Setup summary: Two text deltas plus ResponseCompletedEvent with minimal Response.usage.
    """
    usage = ResponseUsage(
        input_tokens=10,
        input_tokens_details=InputTokensDetails(cached_tokens=0),
        output_tokens=20,
        output_tokens_details=OutputTokensDetails(reasoning_tokens=0),
        total_tokens=30,
    )
    response = Response.model_construct(usage=usage)
    completed = ResponseCompletedEvent.model_construct(
        response=response,
        sequence_number=2,
        type="response.completed",
    )
    events = [
        ResponseTextDeltaEvent(
            content_index=0,
            delta="Hello",
            item_id="msg1",
            logprobs=[],
            output_index=0,
            sequence_number=0,
            type="response.output_text.delta",
        ),
        ResponseTextDeltaEvent(
            content_index=0,
            delta=" world",
            item_id="msg1",
            logprobs=[],
            output_index=0,
            sequence_number=1,
            type="response.output_text.delta",
        ),
        completed,
    ]

    acc = ResponsesStreamAccumulator()
    result = await run_responses_stream_pipeline(
        _responses_events_to_stream(events),
        accumulator=acc,
        message_id="m1",
        chat_id="c1",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert result.message.text == "Hello world"
    assert result.usage is not None
    assert result.usage.prompt_tokens == 10
    assert result.usage.completion_tokens == 20
    assert result.usage.total_tokens == 30


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_run_responses_stream_pipeline_records_function_tool_done() -> None:
    """
    Purpose: Verify ResponseFunctionCallArgumentsDoneEvent becomes LanguageModelFunction.
    Why this matters: Tool streaming must round-trip to toolkit tool_calls.
    Setup summary: One function-call-done event with JSON arguments.
    """
    events = [
        ResponseOutputItemAddedEvent(
            item=ResponseFunctionToolCallItem(
                id="call_1",
                call_id="call_1",
                name="get_weather",
                arguments="{}",
                type="function_call",
            ),
            output_index=0,
            sequence_number=0,
            type="response.output_item.added",
        ),
        ResponseFunctionCallArgumentsDoneEvent(
            arguments='{"city": "Paris"}',
            item_id="call_1",
            output_index=0,
            sequence_number=1,
            type="response.function_call_arguments.done",
        ),
    ]
    acc = ResponsesStreamAccumulator()
    result = await run_responses_stream_pipeline(
        _responses_events_to_stream(events),
        accumulator=acc,
        message_id="m1",
        chat_id="c1",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert result.tool_calls is not None
    assert len(result.tool_calls) == 1
    tc = result.tool_calls[0]
    assert tc.id == "call_1"
    assert tc.name == "get_weather"
    assert tc.arguments == {"city": "Paris"}


class _RecordingPersistence:
    """Strictly typed test double for :class:`ResponseStreamPersistenceProtocol`."""

    def __init__(self) -> None:
        self.indices: list[int] = []
        self.end_called = False

    def reset(self) -> None:
        self.indices = []
        self.end_called = False

    async def on_event(self, event: ResponseStreamEvent, *, index: int) -> None:
        self.indices.append(index)

    async def on_stream_end(self) -> None:
        self.end_called = True


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_run_responses_stream_pipeline_invokes_persistence_in_order() -> None:
    """
    Purpose: Optional persistence receives events in order and a final hook.
    Why this matters: Unique SDK sinks must mirror stream order.
    Setup summary: Two text-delta events and a recording persistence double.
    """
    events = [
        ResponseTextDeltaEvent(
            content_index=0,
            delta="x",
            item_id="msg1",
            logprobs=[],
            output_index=0,
            sequence_number=0,
            type="response.output_text.delta",
        ),
        ResponseTextDeltaEvent(
            content_index=0,
            delta="y",
            item_id="msg1",
            logprobs=[],
            output_index=0,
            sequence_number=1,
            type="response.output_text.delta",
        ),
    ]
    recording = _RecordingPersistence()
    persistence: ResponseStreamPersistenceProtocol = recording
    await run_responses_stream_pipeline(
        _responses_events_to_stream(events),
        accumulator=ResponsesStreamAccumulator(),
        message_id="m1",
        chat_id="c1",
        persistence=persistence,
    )

    assert recording.indices == [0, 1]
    assert recording.end_called is True


@pytest.mark.ai
def test_AI_accumulator_raises_on_second_build_without_reset() -> None:
    """
    Purpose: Double build_stream_result without reset must fail fast.
    Why this matters: Prevents duplicate toolkit responses from one fold.
    Setup summary: build_stream_result twice after the same apply sequence.
    """
    acc = ResponsesStreamAccumulator()
    acc.apply(
        ResponseTextDeltaEvent(
            content_index=0,
            delta="x",
            item_id="m",
            logprobs=[],
            output_index=0,
            sequence_number=0,
            type="response.output_text.delta",
        )
    )
    acc.build_stream_result(
        message_id="m1",
        chat_id="c1",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    with pytest.raises(RuntimeError, match="already produced a result"):
        acc.build_stream_result(
            message_id="m1",
            chat_id="c1",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )


@pytest.mark.ai
def test_AI_accumulator_raises_when_apply_after_build_without_reset() -> None:
    """
    Purpose: Prevent merging a second stream into a finalized fold.
    Why this matters: Reusing one instance across streams must not mix state silently.
    Setup summary: build_stream_result once, then apply() must raise RuntimeError.
    """
    acc = ResponsesStreamAccumulator()
    acc.apply(
        ResponseTextDeltaEvent(
            content_index=0,
            delta="a",
            item_id="m",
            logprobs=[],
            output_index=0,
            sequence_number=0,
            type="response.output_text.delta",
        )
    )
    acc.build_stream_result(
        message_id="m1",
        chat_id="c1",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    with pytest.raises(RuntimeError, match="already produced a result"):
        acc.apply(
            ResponseTextDeltaEvent(
                content_index=0,
                delta="b",
                item_id="m",
                logprobs=[],
                output_index=0,
                sequence_number=1,
                type="response.output_text.delta",
            )
        )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_two_sequential_runs_same_accumulator_do_not_merge_text() -> None:
    """
    Purpose: Runner reset allows safe reuse of one accumulator instance.
    Why this matters: Callers may hold a single accumulator for sequential requests.
    Setup summary: Two run_responses_stream_pipeline calls with the same accumulator.
    """
    acc = ResponsesStreamAccumulator()

    async def stream_a() -> AsyncIterator:
        yield ResponseTextDeltaEvent(
            content_index=0,
            delta="first",
            item_id="m",
            logprobs=[],
            output_index=0,
            sequence_number=0,
            type="response.output_text.delta",
        )

    r1 = await run_responses_stream_pipeline(
        stream_a(),
        accumulator=acc,
        message_id="m1",
        chat_id="c1",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert r1.message.text == "first"

    async def stream_b() -> AsyncIterator:
        yield ResponseTextDeltaEvent(
            content_index=0,
            delta="second",
            item_id="m",
            logprobs=[],
            output_index=0,
            sequence_number=0,
            type="response.output_text.delta",
        )

    r2 = await run_responses_stream_pipeline(
        stream_b(),
        accumulator=acc,
        message_id="m2",
        chat_id="c1",
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    assert r2.message.text == "second"
