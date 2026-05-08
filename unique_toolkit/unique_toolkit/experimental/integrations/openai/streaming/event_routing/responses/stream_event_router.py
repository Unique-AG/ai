"""Responses stream event router — dispatches events to typed event handlers and builds the final result."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeGuard

from openai.types.responses import (
    ResponseCompletedEvent,
    ResponseFunctionCallArgumentsDoneEvent,
    ResponseOutputItemAddedEvent,
    ResponseTextDeltaEvent,
)

from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.content.schemas import ContentChunk, ContentReference
from unique_toolkit.experimental._internal.streaming import (
    AppendixProducer,
    StreamEventHandlerProtocol,
)
from unique_toolkit.experimental._internal.streaming.pattern_replacer import (
    filter_cited_sdk_references,
)
from unique_toolkit.language_model.schemas import ResponsesLanguageModelStreamResponse

from .code_interpreter_event_handler import CodeInterpreterCallEvent

if TYPE_CHECKING:
    from datetime import datetime

    from openai.types.responses import ResponseStreamEvent

    from unique_toolkit._common.event_bus import TypedEventBus
    from unique_toolkit.experimental._internal.streaming import (
        ActivityProgressUpdate,
        TextFlushed,
        TextState,
    )

    from ..protocols import (
        ResponsesCodeInterpreterEventHandlerProtocol,
        ResponsesCompletedEventHandlerProtocol,
        ResponsesTextDeltaEventHandlerProtocol,
        ResponsesToolCallEventHandlerProtocol,
    )


class ResponsesStreamEventRouter:
    """Dispatches ``ResponseStreamEvent`` to typed event handlers and materialises the result.

    Responsibilities (by design, small and disjoint):

    * **Dispatch** — route each ``ResponseStreamEvent`` to the event handler
      whose type it matches (``isinstance`` based). Unknown events are
      ignored for forward compatibility.
    * **Lifecycle fan-out** — ``reset()`` / ``on_stream_end()`` iterate
      every attached event handler.
    * **Bus re-export** — expose ``text_bus`` / ``activity_bus`` so the
      orchestrator can adapt inner-bus events into outer domain events.
    * **Result aggregation** — ``get_text()`` / ``get_appendices()`` /
      ``build_result(...)`` pull accumulated state from event handlers and
      shape the toolkit's final return value.

    Side-effects (``unique_sdk.Message.modify_async``) are the concern of
    :data:`StreamEvent` subscribers on the bus owned by the orchestrator.
    This class is a **router + facade** over the event handlers — no SDK, no
    settings, no bus of its own.
    """

    def __init__(
        self,
        *,
        text_event_handler: ResponsesTextDeltaEventHandlerProtocol,
        tool_call_event_handler: ResponsesToolCallEventHandlerProtocol | None = None,
        completed_event_handler: ResponsesCompletedEventHandlerProtocol | None = None,
        code_interpreter_event_handler: ResponsesCodeInterpreterEventHandlerProtocol
        | None = None,
    ) -> None:
        self._text = text_event_handler
        self._tools = tool_call_event_handler
        self._completed = completed_event_handler
        self._ci = code_interpreter_event_handler

    @property
    def _all_event_handlers(self) -> list[StreamEventHandlerProtocol]:
        return [
            h
            for h in (self._text, self._tools, self._completed, self._ci)
            if h is not None
        ]

    @property
    def text_bus(self) -> TypedEventBus[TextFlushed]:
        """Re-expose the text event handler's flush bus for orchestrator subscription."""
        return self._text.text_bus

    @property
    def activity_bus(self) -> TypedEventBus[ActivityProgressUpdate] | None:
        """Re-expose the code-interpreter event handler's progress bus, if any.

        Returns ``None`` when no code-interpreter event handler is registered.
        Future progress-producing event handlers that want to plug into the
        same bus can share one :class:`TypedEventBus` instance across
        event handlers, or the event routing can grow additional ``*_activity_bus``
        accessors — the adapter pattern in the orchestrator generalises
        without changing the outer event shape.
        """
        if self._ci is None:
            return None
        return self._ci.activity_bus

    def reset(self) -> None:
        for h in self._all_event_handlers:
            h.reset()

    async def on_event(self, event: ResponseStreamEvent) -> None:
        """Dispatch one event to the appropriate event handler.

        All per-event signals (text flushes, tool-activity progress) flow
        through event-handler-owned buses — this method has no return value.
        """
        if isinstance(event, ResponseTextDeltaEvent):
            await self._text.on_text_delta(event)
            return

        if isinstance(event, ResponseOutputItemAddedEvent) and self._tools:
            await self._tools.on_output_item_added(event)
            return

        if isinstance(event, ResponseFunctionCallArgumentsDoneEvent) and self._tools:
            await self._tools.on_function_arguments_done(event)
            return

        if isinstance(event, ResponseCompletedEvent) and self._completed:
            await self._completed.on_completed(event)
            return

        if self._ci and _is_code_interpreter_event(event):
            await self._ci.on_code_interpreter_event(event)
            return

    async def on_stream_end(self) -> None:
        """Finalize all event handlers.

        Any residual replacer text produces a final :class:`TextFlushed`
        on the text event handler's bus before :class:`StreamEnded` is published.
        """
        for h in self._all_event_handlers:
            await h.on_stream_end()

    def get_text(self) -> TextState:
        """Expose the text event handler's accumulated state for orchestrator publishing."""
        return self._text.get_text()

    def get_appendices(self) -> tuple[str, ...]:
        """Collect assistant-message appendices contributed by event handlers.

        Any event handler conforming to :class:`AppendixProducer` can contribute
        text — the result is the ordered concatenation of non-``None``
        appendices. The orchestrator attaches the tuple to
        :class:`StreamEnded` so the message persister writes
        ``full_text + appendices`` in a single round-trip (avoiding a
        retrieve + modify dance).
        """
        appendices: list[str] = []
        for handler in self._all_event_handlers:
            if isinstance(handler, AppendixProducer):
                appendix = handler.get_appendix()
                if appendix is not None:
                    appendices.append(appendix)
        return tuple(appendices)

    def build_result(
        self,
        *,
        message_id: str,
        chat_id: str,
        content_chunks: list[ContentChunk],
        created_at: datetime,
        gpt_request: dict[str, Any] | None = None,
        debug_info: dict[str, Any] | None = None,
    ) -> ResponsesLanguageModelStreamResponse:
        text_state = self._text.get_text()
        tool_calls = self._tools.get_tool_calls() if self._tools else None
        usage = self._completed.get_usage() if self._completed else None
        output = self._completed.get_output() if self._completed else []

        message = ChatMessage(
            id=message_id,
            chat_id=chat_id,
            role=ChatMessageRole.ASSISTANT,
            text=text_state.full_text,
            original_text=text_state.original_text,
            references=[
                ContentReference.from_sdk_reference(r)
                for r in filter_cited_sdk_references(
                    content_chunks, text_state.full_text
                )
            ],
            gpt_request=gpt_request,
            debug_info=debug_info if debug_info is not None else {},
            created_at=created_at,
        )

        return ResponsesLanguageModelStreamResponse(
            message=message,
            tool_calls=tool_calls if tool_calls else None,
            usage=usage,
            output=output,
        )


def _is_code_interpreter_event(
    event: ResponseStreamEvent,
) -> TypeGuard[CodeInterpreterCallEvent]:
    return isinstance(event, CodeInterpreterCallEvent)
