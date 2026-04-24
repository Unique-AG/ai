"""Tests for Chat Completions and Responses streaming pipeline routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest
from openai.types.chat.chat_completion_chunk import (
    ChatCompletionChunk,
    Choice,
    ChoiceDelta,
    ChoiceDeltaToolCall,
)
from openai.types.responses import (
    ResponseFunctionCallArgumentsDoneEvent,
    ResponseOutputItemAddedEvent,
    ResponseTextDeltaEvent,
)
from openai.types.responses.response_function_tool_call_item import (
    ResponseFunctionToolCallItem,
)
from openai.types.responses.response_text_delta_event import Logprob

from unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completions.stream_pipeline import (
    ChatCompletionStreamPipeline,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.protocols import (
    TextState,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.completed_handler import (
    ResponsesCompletedHandler,
    _extract_usage,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.stream_pipeline import (
    ResponsesStreamPipeline,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.tool_call_handler import (
    ResponsesToolCallHandler,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelTokenUsage,
)


def _chat_chunk(
    *,
    content: str | None = None,
    tool_calls: list[ChoiceDeltaToolCall] | None = None,
) -> ChatCompletionChunk:
    return ChatCompletionChunk.model_construct(
        id="chunk-1",
        choices=[
            Choice.model_construct(
                index=0,
                delta=ChoiceDelta.model_construct(
                    content=content, tool_calls=tool_calls
                ),
            )
        ],
        created=0,
        model="gpt-test",
        object="chat.completion.chunk",
    )


@dataclass
class _FakeChatTextHandler:
    """Fake text handler: records chunks and reports a configurable flush flag.

    The new protocol makes ``on_chunk`` / ``on_stream_end`` return ``bool``
    (flush boundary). Tests exercise both routing and the flag plumbing.
    """

    chunks: list[tuple[int, ChatCompletionChunk]] = field(default_factory=list)
    ends: int = 0
    flush: bool = False
    end_flush: bool = False
    state: TextState = field(
        default_factory=lambda: TextState(full_text="hello", original_text="raw")
    )

    async def on_chunk(self, event: ChatCompletionChunk, *, index: int) -> bool:
        self.chunks.append((index, event))
        return self.flush

    async def on_stream_end(self) -> bool:
        self.ends += 1
        return self.end_flush

    def get_text(self) -> TextState:
        return self.state

    def reset(self) -> None:
        self.chunks.clear()
        self.ends = 0


@dataclass
class _FakeChatToolHandler:
    calls: list[ChatCompletionChunk] = field(default_factory=list)
    ends: int = 0
    tools: list[LanguageModelFunction] = field(default_factory=list)

    async def on_chunk(self, event: ChatCompletionChunk) -> None:
        self.calls.append(event)

    async def on_stream_end(self) -> None:
        self.ends += 1

    def get_tool_calls(self) -> list[LanguageModelFunction]:
        return self.tools

    def reset(self) -> None:
        self.calls.clear()
        self.ends = 0


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_chat_completion_stream_pipeline__on_event__forwards_to_both_handlers():
    """
    Purpose: Verify each chunk is passed to text and tool handlers.
    Why this matters: Chat chunks may carry content and tool deltas together; both paths must run.
    Setup summary: Fake handlers; await on_event with a chunk; assert both recorded the same event.
    """
    text_h = _FakeChatTextHandler()
    tool_h = _FakeChatToolHandler()
    pipe = ChatCompletionStreamPipeline(text_handler=text_h, tool_call_handler=tool_h)
    chunk = _chat_chunk(content="hi")
    await pipe.on_event(chunk, index=2)
    assert text_h.chunks == [(2, chunk)]
    assert tool_h.calls == [chunk]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_chat_completion_stream_pipeline__on_event__returns_text_flush_flag():
    """
    Purpose: ``on_event`` must surface the text handler's flush boundary.
    Why this matters: The orchestrator uses this bool to decide when to publish ``TextDelta``.
    Setup summary: Fake text handler configured to return True; assert pipeline returns True.
    """
    text_h = _FakeChatTextHandler(flush=True)
    pipe = ChatCompletionStreamPipeline(text_handler=text_h)
    flushed = await pipe.on_event(_chat_chunk(content="x"), index=0)
    assert flushed is True


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_chat_completion_stream_pipeline__on_stream_end__finalizes_all_handlers():
    """
    Purpose: Ensure ``on_stream_end`` calls every registered handler.
    Why this matters: Handlers flush replacer buffers and release resources.
    Setup summary: Fakes for text + tool; assert both have ``ends == 1`` after call.
    """
    text_h = _FakeChatTextHandler()
    tool_h = _FakeChatToolHandler()
    pipe = ChatCompletionStreamPipeline(text_handler=text_h, tool_call_handler=tool_h)
    await pipe.on_stream_end()
    assert text_h.ends == 1
    assert tool_h.ends == 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_chat_completion_stream_pipeline__on_stream_end__returns_residual_flush():
    """
    Purpose: ``on_stream_end`` propagates the text handler's residual flush flag.
    Why this matters: Replacer buffers may hold trailing characters that need a final emit.
    Setup summary: Fake text handler with ``end_flush=True``; assert pipeline returns True.
    """
    text_h = _FakeChatTextHandler(end_flush=True)
    pipe = ChatCompletionStreamPipeline(text_handler=text_h)
    flushed = await pipe.on_stream_end()
    assert flushed is True


@pytest.mark.ai
def test_AI_chat_completion_stream_pipeline__build_result__includes_tool_calls():
    """
    Purpose: Check build_result merges text state and optional tool calls into the response DTO.
    Why this matters: Callers consume LanguageModelStreamResponse after streaming.
    Setup summary: Fake handlers with tool_calls; build_result; assert message text and tools.
    """
    text_h = _FakeChatTextHandler()
    tool_fn = LanguageModelFunction(name="t", arguments={"a": 1})
    tool_h = _FakeChatToolHandler(tools=[tool_fn])
    pipe = ChatCompletionStreamPipeline(text_handler=text_h, tool_call_handler=tool_h)
    from datetime import datetime, timezone

    created = datetime.now(timezone.utc)
    result = pipe.build_result(message_id="m1", chat_id="c1", created_at=created)
    assert result.message.text == "hello"
    assert result.tool_calls == [tool_fn]


@pytest.mark.ai
def test_AI_chat_completion_stream_pipeline__get_text__delegates_to_text_handler():
    """
    Purpose: The pipeline exposes the text handler's accumulated state.
    Why this matters: Orchestrators publish ``TextDelta`` using this state — keeping the access
      path on the pipeline (not the handler directly) avoids leaking handler internals.
    Setup summary: Fake handler with fixed state; ``get_text()`` returns it.
    """
    text_h = _FakeChatTextHandler(state=TextState(full_text="a", original_text="b"))
    pipe = ChatCompletionStreamPipeline(text_handler=text_h)
    s = pipe.get_text()
    assert s.full_text == "a"
    assert s.original_text == "b"


@dataclass
class _FakeResponsesText:
    deltas: list[ResponseTextDeltaEvent] = field(default_factory=list)
    ends: int = 0
    flush: bool = False
    end_flush: bool = False
    state: TextState = field(
        default_factory=lambda: TextState(full_text="t", original_text="o")
    )

    async def on_text_delta(self, event: ResponseTextDeltaEvent) -> bool:
        self.deltas.append(event)
        return self.flush

    async def on_stream_end(self) -> bool:
        self.ends += 1
        return self.end_flush

    def get_text(self) -> TextState:
        return self.state

    def reset(self) -> None:
        self.deltas.clear()
        self.ends = 0


@dataclass
class _FakeCompleted:
    events: list[object] = field(default_factory=list)
    ends: int = 0
    usage: LanguageModelTokenUsage | None = None
    output: list = field(default_factory=list)

    async def on_completed(self, event: object) -> None:
        self.events.append(event)

    async def on_stream_end(self) -> None:
        self.ends += 1

    def get_usage(self) -> LanguageModelTokenUsage | None:
        return self.usage

    def get_output(self) -> list:
        return self.output

    def reset(self) -> None:
        self.events.clear()
        self.ends = 0


def _text_delta(delta: str) -> ResponseTextDeltaEvent:
    return ResponseTextDeltaEvent(
        type="response.output_text.delta",
        delta=delta,
        item_id="it1",
        output_index=0,
        content_index=0,
        sequence_number=1,
        logprobs=[Logprob(token="x", logprob=0.0)],
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_responses_stream_pipeline__on_event__routes_text_delta_and_returns_flush():
    """
    Purpose: ResponseTextDeltaEvent should reach only the text handler and propagate its flush flag.
    Why this matters: Wrong routing would drop tokens; a missing flush flag would suppress TextDelta events.
    Setup summary: Fake text + completed handlers (text flushes); send delta; assert routing + return True.
    """
    text_h = _FakeResponsesText(flush=True)
    done_h = _FakeCompleted()
    pipe = ResponsesStreamPipeline(text_handler=text_h, completed_handler=done_h)
    ev = _text_delta("abc")
    flushed = await pipe.on_event(ev)
    assert text_h.deltas == [ev]
    assert done_h.events == []
    assert flushed is True


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_responses_stream_pipeline__on_event__non_text_events_return_false():
    """
    Purpose: Non-text events must return False so the orchestrator doesn't publish stale TextDelta.
    Why this matters: Tool / completion events don't change the accumulated text.
    Setup summary: Route an output-item-added event through the pipeline; assert False.
    """
    text_h = _FakeResponsesText()
    tools = ResponsesToolCallHandler()
    pipe = ResponsesStreamPipeline(text_handler=text_h, tool_call_handler=tools)
    item = ResponseFunctionToolCallItem.model_construct(
        id="call-item-1",
        status="in_progress",
        arguments="",
        call_id="cid",
        name="lookup",
        type="function_call",
    )
    added = ResponseOutputItemAddedEvent.model_construct(
        item=item,
        output_index=0,
        sequence_number=1,
        type="response.output_item.added",
    )
    flushed = await pipe.on_event(added)
    assert flushed is False


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_responses_stream_pipeline__tool_flow__records_function_call():
    """
    Purpose: Output-item + arguments-done events should produce a tool call on the handler.
    Why this matters: Downstream execution needs parsed name and arguments from the stream.
    Setup summary: Real ResponsesToolCallHandler; simulate added item then arguments JSON.
    """
    text_h = _FakeResponsesText()
    tools = ResponsesToolCallHandler()
    pipe = ResponsesStreamPipeline(text_handler=text_h, tool_call_handler=tools)
    item = ResponseFunctionToolCallItem.model_construct(
        id="call-item-1",
        status="in_progress",
        arguments="",
        call_id="cid",
        name="lookup",
        type="function_call",
    )
    added = ResponseOutputItemAddedEvent.model_construct(
        item=item,
        output_index=0,
        sequence_number=1,
        type="response.output_item.added",
    )
    await pipe.on_event(added)
    done = ResponseFunctionCallArgumentsDoneEvent.model_construct(
        type="response.function_call_arguments.done",
        item_id="call-item-1",
        name="lookup",
        arguments='{"q":"x"}',
        output_index=0,
        sequence_number=2,
    )
    await pipe.on_event(done)
    calls = tools.get_tool_calls()
    assert len(calls) == 1
    assert calls[0].name == "lookup"
    assert calls[0].arguments == {"q": "x"}


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_responses_stream_pipeline__on_stream_end__invokes_all_handlers():
    """
    Purpose: on_stream_end must finalize every registered handler.
    Why this matters: Handlers flush buffers and release resources.
    Setup summary: Fakes for text and completed; await on_stream_end; both ends counters increment.
    """
    text_h = _FakeResponsesText()
    done_h = _FakeCompleted()
    pipe = ResponsesStreamPipeline(text_handler=text_h, completed_handler=done_h)
    await pipe.on_stream_end()
    assert text_h.ends == 1
    assert done_h.ends == 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_responses_stream_pipeline__on_stream_end__propagates_residual_flush():
    """
    Purpose: Pipeline returns the text handler's residual flush flag from on_stream_end.
    Why this matters: Lets the orchestrator publish a final TextDelta before StreamEnded.
    Setup summary: Fake text handler with end_flush=True; assert pipeline returns True.
    """
    text_h = _FakeResponsesText(end_flush=True)
    pipe = ResponsesStreamPipeline(text_handler=text_h)
    assert await pipe.on_stream_end() is True


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_responses_completed_handler__on_completed__extracts_usage_and_output():
    """
    Purpose: Map OpenAI Response usage fields into LanguageModelTokenUsage.
    Why this matters: Billing and limits use prompt/completion/total token counts.
    Setup summary: Build minimal event object; on_completed; assert usage and output list.
    """
    handler = ResponsesCompletedHandler()
    usage_obj = SimpleNamespace(input_tokens=3, output_tokens=5, total_tokens=8)
    out_item = object()
    response = SimpleNamespace(usage=usage_obj, output=[out_item])
    event = SimpleNamespace(response=response)
    await handler.on_completed(event)  # type: ignore[arg-type]
    u = handler.get_usage()
    assert u is not None
    assert u.prompt_tokens == 3
    assert u.completion_tokens == 5
    assert u.total_tokens == 8
    assert handler.get_output() == [out_item]


@pytest.mark.ai
def test_AI_extract_usage__returns_none_when_missing():
    """
    Purpose: _extract_usage handles responses with no usage block.
    Why this matters: Some streams or errors omit usage without breaking callers.
    Setup summary: Response.usage is None; assert _extract_usage returns None.
    """
    event = SimpleNamespace(response=SimpleNamespace(usage=None))
    assert _extract_usage(event) is None  # type: ignore[arg-type]


@pytest.mark.ai
def test_AI_responses_stream_pipeline__build_result__includes_usage_and_original_text():
    """
    Purpose: build_result should surface text, usage, and output from handlers.
    Why this matters: Streaming API consumers need a single aggregate result object.
    Setup summary: Wire fakes with usage/output set; build_result; assert fields on DTO.
    """
    from datetime import datetime, timezone

    text_h = _FakeResponsesText()
    text_h.state = TextState(full_text="n", original_text="orig")
    done_h = _FakeCompleted()
    done_h.usage = LanguageModelTokenUsage(
        prompt_tokens=1, completion_tokens=2, total_tokens=3
    )
    done_h.output = []  # pydantic validates the union; empty list is sufficient here.
    pipe = ResponsesStreamPipeline(text_handler=text_h, completed_handler=done_h)
    created = datetime.now(timezone.utc)
    r = pipe.build_result(message_id="m", chat_id="c", created_at=created)
    assert r.message.text == "n"
    assert r.message.original_text == "orig"
    assert r.usage is not None
    assert r.usage.total_tokens == 3
    assert r.output == []
