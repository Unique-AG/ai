"""Tests for Chat Completions and Responses streaming pipeline routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from openai.types.chat.chat_completion_chunk import (
    ChatCompletionChunk,
    Choice,
    ChoiceDelta,
    ChoiceDeltaToolCall,
    ChoiceDeltaToolCallFunction,
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
from pydantic import SecretStr

from unique_toolkit.app.unique_settings import (
    AuthContext,
    ChatContext,
    UniqueApi,
    UniqueApp,
    UniqueContext,
    UniqueSettings,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completions.stream_pipeline import (
    ChatCompletionStreamPipeline,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.protocols import TextState
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
from unique_toolkit.language_model.schemas import LanguageModelFunction, LanguageModelTokenUsage


def _settings_with_chat() -> UniqueSettings:
    auth = AuthContext(
        user_id=SecretStr("user-1"), company_id=SecretStr("company-1")
    )
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
    settings: UniqueSettings
    chunks: list[tuple[int, ChatCompletionChunk]] = field(default_factory=list)
    ends: int = 0
    state: TextState = field(
        default_factory=lambda: TextState(full_text="hello", original_text="raw")
    )

    async def on_chunk(self, event: ChatCompletionChunk, *, index: int) -> None:
        self.chunks.append((index, event))

    async def on_stream_end(self) -> None:
        self.ends += 1

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
async def test_chat_completion_stream_pipeline__on_event__forwards_to_both_handlers():
    """
    Purpose: Verify each chunk is passed to text and tool handlers.
    Why this matters: Chat chunks may carry content and tool deltas together; both paths must run.
    Setup summary: Fake handlers; await on_event with a chunk; assert both recorded the same event.
    """
    settings = _settings_with_chat()
    text_h = _FakeChatTextHandler(settings=settings)
    tool_h = _FakeChatToolHandler()
    pipe = ChatCompletionStreamPipeline(
        text_handler=text_h, tool_call_handler=tool_h, settings=settings
    )
    chunk = _chat_chunk(content="hi")
    await pipe.on_event(chunk, index=2)
    assert text_h.chunks == [(2, chunk)]
    assert tool_h.calls == [chunk]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_chat_completion_stream_pipeline__on_stream_end__sets_completed_at():
    """
    Purpose: Ensure stream completion updates the assistant message via the SDK.
    Why this matters: Clients rely on completedAt to know generation finished.
    Setup summary: Patch Message.modify_async; await on_stream_end; assert called with completedAt.
    """
    settings = _settings_with_chat()
    text_h = _FakeChatTextHandler(settings=settings)
    pipe = ChatCompletionStreamPipeline(text_handler=text_h, settings=settings)
    with patch(
        "unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completions.stream_pipeline.unique_sdk.Message.modify_async",
        new_callable=AsyncMock,
    ) as modify:
        await pipe.on_stream_end()
    modify.assert_called_once()
    kwargs = modify.call_args.kwargs
    assert kwargs["id"] == "amsg-1"
    assert kwargs["chatId"] == "chat-1"
    assert "completedAt" in kwargs


@pytest.mark.ai
@pytest.mark.asyncio
async def test_chat_completion_stream_pipeline__on_stream_end__raises_without_chat():
    """
    Purpose: Fail fast when chat context is missing at stream end.
    Why this matters: Avoids silent SDK calls with invalid IDs.
    Setup summary: Settings with chat=None; expect ValueError from on_stream_end.
    """
    auth = AuthContext(
        user_id=SecretStr("user-1"), company_id=SecretStr("company-1")
    )
    settings = UniqueSettings(auth=auth, app=UniqueApp(), api=UniqueApi())
    text_h = _FakeChatTextHandler(settings=settings)
    pipe = ChatCompletionStreamPipeline(text_handler=text_h, settings=settings)
    with pytest.raises(ValueError, match="Chat is not set"):
        await pipe.on_stream_end()


@pytest.mark.ai
def test_chat_completion_stream_pipeline__build_result__includes_tool_calls():
    """
    Purpose: Check build_result merges text state and optional tool calls into the response DTO.
    Why this matters: Callers consume LanguageModelStreamResponse after streaming.
    Setup summary: Fake handlers with tool_calls; build_result; assert message text and tools.
    """
    settings = _settings_with_chat()
    text_h = _FakeChatTextHandler(settings=settings)
    tool_fn = LanguageModelFunction(name="t", arguments={"a": 1})
    tool_h = _FakeChatToolHandler(tools=[tool_fn])
    pipe = ChatCompletionStreamPipeline(
        text_handler=text_h, tool_call_handler=tool_h, settings=settings
    )
    from datetime import datetime, timezone

    created = datetime.now(timezone.utc)
    result = pipe.build_result(
        message_id="m1", chat_id="c1", created_at=created
    )
    assert result.message.text == "hello"
    assert result.tool_calls == [tool_fn]


@pytest.mark.ai
def test_chat_completion_stream_pipeline__init__requires_settings_for_generic_text_handler():
    """
    Purpose: Constructor must receive settings when text handler is not ChatCompletionTextHandler.
    Why this matters: Generic protocol implementations have no _settings to infer from.
    Setup summary: Pass a fake text handler without settings kwarg; expect TypeError.
    """
    settings = _settings_with_chat()
    text_h = _FakeChatTextHandler(settings=settings)
    with pytest.raises(TypeError, match="settings is required"):
        ChatCompletionStreamPipeline(text_handler=text_h)


@dataclass
class _FakeResponsesText:
    deltas: list[ResponseTextDeltaEvent] = field(default_factory=list)
    ends: int = 0
    state: TextState = field(
        default_factory=lambda: TextState(full_text="t", original_text="o")
    )

    async def on_text_delta(self, event: ResponseTextDeltaEvent) -> None:
        self.deltas.append(event)

    async def on_stream_end(self) -> None:
        self.ends += 1

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
async def test_responses_stream_pipeline__on_event__routes_text_delta():
    """
    Purpose: ResponseTextDeltaEvent should reach only the text handler.
    Why this matters: Wrong routing would drop assistant tokens or double-handle events.
    Setup summary: Fake text + completed handlers; send text delta; assert text handler saw it.
    """
    text_h = _FakeResponsesText()
    done_h = _FakeCompleted()
    pipe = ResponsesStreamPipeline(
        text_handler=text_h, completed_handler=done_h
    )
    ev = _text_delta("abc")
    await pipe.on_event(ev)
    assert text_h.deltas == [ev]
    assert done_h.events == []


@pytest.mark.ai
@pytest.mark.asyncio
async def test_responses_stream_pipeline__tool_flow__records_function_call():
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
async def test_responses_stream_pipeline__on_stream_end__invokes_all_handlers():
    """
    Purpose: on_stream_end must finalize every registered handler.
    Why this matters: Handlers flush buffers and persist final state.
    Setup summary: Fakes for text and completed; await on_stream_end; both ends counters increment.
    """
    text_h = _FakeResponsesText()
    done_h = _FakeCompleted()
    pipe = ResponsesStreamPipeline(
        text_handler=text_h, completed_handler=done_h
    )
    await pipe.on_stream_end()
    assert text_h.ends == 1
    assert done_h.ends == 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_responses_completed_handler__on_completed__extracts_usage_and_output():
    """
    Purpose: Map OpenAI Response usage fields into LanguageModelTokenUsage.
    Why this matters: Billing and limits use prompt/completion/total token counts.
    Setup summary: Build minimal event object; on_completed; assert usage and output list.
    """
    handler = ResponsesCompletedHandler()
    usage_obj = SimpleNamespace(
        input_tokens=3, output_tokens=5, total_tokens=8
    )
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
def test_extract_usage__returns_none_when_missing():
    """
    Purpose: _extract_usage handles responses with no usage block.
    Why this matters: Some streams or errors omit usage without breaking callers.
    Setup summary: Response.usage is None; assert _extract_usage returns None.
    """
    event = SimpleNamespace(response=SimpleNamespace(usage=None))
    assert _extract_usage(event) is None  # type: ignore[arg-type]


@pytest.mark.ai
def test_responses_stream_pipeline__build_result__includes_usage_and_original_text():
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
    marker = object()
    done_h.output = [marker]  # type: ignore[list-item]
    pipe = ResponsesStreamPipeline(
        text_handler=text_h, completed_handler=done_h
    )
    created = datetime.now(timezone.utc)
    r = pipe.build_result(message_id="m", chat_id="c", created_at=created)
    assert r.message.text == "n"
    assert r.message.original_text == "orig"
    assert r.usage is not None
    assert r.usage.total_tokens == 3
    assert r.output == [marker]
