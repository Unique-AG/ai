"""Tests for Chat Completions and Responses stream event routing."""

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

from unique_toolkit._common.event_bus import TypedEventBus
from unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completions.stream_event_router import (
    ChatCompletionStreamEventRouter,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.protocols import (
    TextFlushed,
    TextState,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.completed_handler import (
    ResponsesCompletedHandler,
    _extract_usage,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.stream_event_router import (
    ResponsesStreamEventRouter,
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
    """Fake text handler: records chunks and publishes configurable flushes.

    The new protocol replaces the bool return value with a handler-owned
    :class:`TypedEventBus` carrying :class:`TextFlushed`. Tests exercise
    both routing and the bus-publish plumbing by subscribing to the
    router's ``text_bus``.
    """

    chunks: list[tuple[int, ChatCompletionChunk]] = field(default_factory=list)
    ends: int = 0
    flush: bool = False
    end_flush: bool = False
    state: TextState = field(
        default_factory=lambda: TextState(full_text="hello", original_text="raw")
    )
    text_bus: TypedEventBus[TextFlushed] = field(default_factory=TypedEventBus)

    async def on_chunk(self, event: ChatCompletionChunk, *, index: int) -> None:
        self.chunks.append((index, event))
        if self.flush:
            await self.text_bus.publish_and_wait_async(
                TextFlushed(
                    full_text=self.state.full_text,
                    original_text=self.state.original_text,
                    chunk_index=index,
                )
            )

    async def on_stream_end(self) -> None:
        self.ends += 1
        if self.end_flush:
            await self.text_bus.publish_and_wait_async(
                TextFlushed(
                    full_text=self.state.full_text,
                    original_text=self.state.original_text,
                )
            )

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
async def test_AI_chat_completion_stream_event_router__on_event__forwards_to_both_handlers():
    """
    Purpose: Verify each chunk is passed to text and tool handlers.
    Why this matters: Chat chunks may carry content and tool deltas together; both paths must run.
    Setup summary: Fake handlers; await on_event with a chunk; assert both recorded the same event.
    """
    text_h = _FakeChatTextHandler()
    tool_h = _FakeChatToolHandler()
    router = ChatCompletionStreamEventRouter(
        text_handler=text_h, tool_call_handler=tool_h
    )
    chunk = _chat_chunk(content="hi")
    await router.on_event(chunk, index=2)
    assert text_h.chunks == [(2, chunk)]
    assert tool_h.calls == [chunk]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_chat_completion_stream_event_router__on_event__propagates_flush_via_bus():
    """
    Purpose: ``on_event`` must propagate the text handler's flush via the bus.
    Why this matters: The orchestrator subscribes to ``text_bus`` to decide
      when to publish :class:`TextDelta` — the router must re-expose the
      handler's bus faithfully.
    Setup summary: Fake text handler configured to flush; subscribe to the
      router's ``text_bus``; assert exactly one :class:`TextFlushed`
      is received.
    """
    text_h = _FakeChatTextHandler(flush=True)
    router = ChatCompletionStreamEventRouter(text_handler=text_h)
    received: list[TextFlushed] = []
    router.text_bus.subscribe(received.append)
    await router.on_event(_chat_chunk(content="x"), index=0)
    assert len(received) == 1
    assert received[0].full_text == "hello"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_chat_completion_stream_event_router__on_stream_end__finalizes_all_handlers():
    """
    Purpose: Ensure ``on_stream_end`` calls every registered handler.
    Why this matters: Handlers flush replacer buffers and release resources.
    Setup summary: Fakes for text + tool; assert both have ``ends == 1`` after call.
    """
    text_h = _FakeChatTextHandler()
    tool_h = _FakeChatToolHandler()
    router = ChatCompletionStreamEventRouter(
        text_handler=text_h, tool_call_handler=tool_h
    )
    await router.on_stream_end()
    assert text_h.ends == 1
    assert tool_h.ends == 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_chat_completion_stream_event_router__on_stream_end__publishes_residual_flush():
    """
    Purpose: ``on_stream_end`` causes a residual :class:`TextFlushed` publish.
    Why this matters: Replacer buffers may hold trailing characters that need
      a final emit before :class:`StreamEnded` is published.
    Setup summary: Fake text handler with ``end_flush=True``; subscribe to
      the router's ``text_bus``; assert one event is received.
    """
    text_h = _FakeChatTextHandler(end_flush=True)
    router = ChatCompletionStreamEventRouter(text_handler=text_h)
    received: list[TextFlushed] = []
    router.text_bus.subscribe(received.append)
    await router.on_stream_end()
    assert len(received) == 1


@pytest.mark.ai
def test_AI_chat_completion_stream_event_router__build_result__includes_tool_calls():
    """
    Purpose: Check build_result merges text state and optional tool calls into the response DTO.
    Why this matters: Callers consume LanguageModelStreamResponse after streaming.
    Setup summary: Fake handlers with tool_calls; build_result; assert message text and tools.
    """
    text_h = _FakeChatTextHandler()
    tool_fn = LanguageModelFunction(name="t", arguments={"a": 1})
    tool_h = _FakeChatToolHandler(tools=[tool_fn])
    router = ChatCompletionStreamEventRouter(
        text_handler=text_h, tool_call_handler=tool_h
    )
    from datetime import datetime, timezone

    created = datetime.now(timezone.utc)
    result = router.build_result(message_id="m1", chat_id="c1", created_at=created)
    assert result.message.text == "hello"
    assert result.tool_calls == [tool_fn]


@pytest.mark.ai
def test_AI_chat_completion_stream_event_router__get_text__delegates_to_text_handler():
    """
    Purpose: The router exposes the text handler's accumulated state.
    Why this matters: Orchestrators publish ``TextDelta`` using this state — keeping the access
      path on the router (not the handler directly) avoids leaking handler internals.
    Setup summary: Fake handler with fixed state; ``get_text()`` returns it.
    """
    text_h = _FakeChatTextHandler(state=TextState(full_text="a", original_text="b"))
    router = ChatCompletionStreamEventRouter(text_handler=text_h)
    s = router.get_text()
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
    text_bus: TypedEventBus[TextFlushed] = field(default_factory=TypedEventBus)

    async def on_text_delta(self, event: ResponseTextDeltaEvent) -> None:
        self.deltas.append(event)
        if self.flush:
            await self.text_bus.publish_and_wait_async(
                TextFlushed(
                    full_text=self.state.full_text,
                    original_text=self.state.original_text,
                )
            )

    async def on_stream_end(self) -> None:
        self.ends += 1
        if self.end_flush:
            await self.text_bus.publish_and_wait_async(
                TextFlushed(
                    full_text=self.state.full_text,
                    original_text=self.state.original_text,
                )
            )

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
async def test_AI_responses_stream_event_router__on_event__routes_text_delta_and_publishes_flush():
    """
    Purpose: ResponseTextDeltaEvent should reach only the text handler and trigger a flush publish.
    Why this matters: Wrong routing would drop tokens; a missing flush publish would suppress TextDelta events.
    Setup summary: Fake text + completed handlers (text flushes); subscribe to
      the router's ``text_bus``; send delta; assert routing + one bus
      publish received.
    """
    text_h = _FakeResponsesText(flush=True)
    done_h = _FakeCompleted()
    router = ResponsesStreamEventRouter(text_handler=text_h, completed_handler=done_h)
    received: list[TextFlushed] = []
    router.text_bus.subscribe(received.append)
    ev = _text_delta("abc")
    await router.on_event(ev)
    assert text_h.deltas == [ev]
    assert done_h.events == []
    assert len(received) == 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_responses_stream_event_router__on_event__non_text_events_do_not_publish_flush():
    """
    Purpose: Non-text events must not trigger a flush publish on ``text_bus``.
    Why this matters: Tool / completion events don't change the accumulated text;
      spurious publishes would produce stale :class:`TextDelta` events.
    Setup summary: Route an output-item-added event through the router; assert
      the flush bus received nothing.
    """
    text_h = _FakeResponsesText()
    tools = ResponsesToolCallHandler()
    router = ResponsesStreamEventRouter(text_handler=text_h, tool_call_handler=tools)
    received: list[TextFlushed] = []
    router.text_bus.subscribe(received.append)
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
    await router.on_event(added)
    assert received == []


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_responses_stream_event_router__tool_flow__records_function_call():
    """
    Purpose: Output-item + arguments-done events should produce a tool call on the handler.
    Why this matters: Downstream execution needs parsed name and arguments from the stream.
    Setup summary: Real ResponsesToolCallHandler; simulate added item then arguments JSON.
    """
    text_h = _FakeResponsesText()
    tools = ResponsesToolCallHandler()
    router = ResponsesStreamEventRouter(text_handler=text_h, tool_call_handler=tools)
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
    await router.on_event(added)
    done = ResponseFunctionCallArgumentsDoneEvent.model_construct(
        type="response.function_call_arguments.done",
        item_id="call-item-1",
        name="lookup",
        arguments='{"q":"x"}',
        output_index=0,
        sequence_number=2,
    )
    await router.on_event(done)
    calls = tools.get_tool_calls()
    assert len(calls) == 1
    assert calls[0].name == "lookup"
    assert calls[0].arguments == {"q": "x"}


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_responses_stream_event_router__on_stream_end__invokes_all_handlers():
    """
    Purpose: on_stream_end must finalize every registered handler.
    Why this matters: Handlers flush buffers and release resources.
    Setup summary: Fakes for text and completed; await on_stream_end; both ends counters increment.
    """
    text_h = _FakeResponsesText()
    done_h = _FakeCompleted()
    router = ResponsesStreamEventRouter(text_handler=text_h, completed_handler=done_h)
    await router.on_stream_end()
    assert text_h.ends == 1
    assert done_h.ends == 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_responses_stream_event_router__on_stream_end__publishes_residual_flush():
    """
    Purpose: Pipeline publishes a residual :class:`TextFlushed` on ``on_stream_end``.
    Why this matters: Lets the orchestrator publish a final :class:`TextDelta`
      before :class:`StreamEnded`.
    Setup summary: Fake text handler with ``end_flush=True``; subscribe to
      the flush bus; assert one event received.
    """
    text_h = _FakeResponsesText(end_flush=True)
    router = ResponsesStreamEventRouter(text_handler=text_h)
    received: list[TextFlushed] = []
    router.text_bus.subscribe(received.append)
    await router.on_stream_end()
    assert len(received) == 1


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
def test_AI_responses_stream_event_router__build_result__includes_usage_and_original_text():
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
    router = ResponsesStreamEventRouter(text_handler=text_h, completed_handler=done_h)
    created = datetime.now(timezone.utc)
    r = router.build_result(message_id="m", chat_id="c", created_at=created)
    assert r.message.text == "n"
    assert r.message.original_text == "orig"
    assert r.usage is not None
    assert r.usage.total_tokens == 3
    assert r.output == []
