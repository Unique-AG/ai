"""Chat Completions stream event router — dispatches chunks to typed event handlers and builds the final result."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.content.schemas import ContentChunk, ContentReference
from unique_toolkit.experimental._internal.streaming import StreamEventHandlerProtocol
from unique_toolkit.experimental._internal.streaming.pattern_replacer import (
    filter_cited_sdk_references,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelStreamResponse,
    LanguageModelTokenUsage,
)

if TYPE_CHECKING:
    from datetime import datetime

    from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

    from unique_toolkit._common.event_bus import TypedEventBus
    from unique_toolkit.experimental._internal.streaming import TextFlushed

    from ..protocols import (
        ChatCompletionTextEventHandlerProtocol,
        ChatCompletionToolCallEventHandlerProtocol,
    )


class ChatCompletionStreamEventRouter:
    """Dispatches ``ChatCompletionChunk`` to typed event handlers and materialises the result.

    Unlike the Responses router where event types are distinct, a single
    ``ChatCompletionChunk`` can carry both content and tool call deltas,
    so both event handlers receive every chunk (a **broadcast** dispatch) and
    each event handler inspects the chunk internally.

    Responsibilities (by design, small and disjoint):

    * **Dispatch (broadcast)** — every ``ChatCompletionChunk`` is sent to
      the text event handler and, if attached, the tool-call event handler.
    * **Lifecycle fan-out** — ``reset()`` / ``on_stream_end()`` iterate
      every attached event handler.
    * **Bus re-export** — ``text_bus`` is re-exposed so the orchestrator
      can adapt inner-bus flushes into outer :class:`TextDelta` events.
    * **Result aggregation** — ``get_text()`` / ``build_result(...)``
      pull accumulated state from event handlers and shape the toolkit result.

    Side-effects (``unique_sdk.Message.modify_async`` for references,
    timestamps, completion) are published as :data:`StreamEvent` on the
    bus owned by the orchestrator. This class is a **router + facade**
    over stateful event handlers — no SDK, no settings, no bus of its own.
    """

    def __init__(
        self,
        *,
        text_event_handler: ChatCompletionTextEventHandlerProtocol,
        tool_call_event_handler: ChatCompletionToolCallEventHandlerProtocol
        | None = None,
    ) -> None:
        self._text = text_event_handler
        self._tools = tool_call_event_handler

    @property
    def _all_event_handlers(self) -> list[StreamEventHandlerProtocol]:
        return [h for h in (self._text, self._tools) if h is not None]

    @property
    def text_bus(self) -> TypedEventBus[TextFlushed]:
        """Re-expose the text event handler's flush bus for orchestrator subscription.

        Subscribers (typically the orchestrator) attach once at construction
        and receive a :class:`TextFlushed` on every flush boundary crossed
        during streaming — no explicit drain/pull required.
        """
        return self._text.text_bus

    def reset(self) -> None:
        for h in self._all_event_handlers:
            h.reset()

    async def on_event(self, event: ChatCompletionChunk) -> None:
        """Dispatch one chunk to text + tool event handlers.

        Text flushes are published on the text event handler's
        :attr:`text_bus`; the tool event handler has no per-event
        side-effect surface (final tool calls are read at stream end).
        """
        await self._text.on_chunk(event)
        if self._tools:
            await self._tools.on_chunk(event)

    async def on_stream_end(self) -> None:
        """Finalize all event handlers.

        Any residual replacer text produces a final :class:`TextFlushed`
        on the text event handler's bus before the orchestrator publishes
        :class:`StreamEnded`.
        """
        await self._text.on_stream_end()
        if self._tools:
            await self._tools.on_stream_end()

    @property
    def text(self):
        """Expose the text event handler's accumulated state for orchestrator publishing."""
        return self._text.get_text()

    def get_text(self):
        """Expose the text event handler's accumulated state for result aggregation."""
        return self._text.get_text()

    @property
    def tool_calls(self) -> list[LanguageModelFunction] | None:
        return self._tools.get_tool_calls() if self._tools else None

    @property
    def usage(self) -> LanguageModelTokenUsage | None:
        """Expose token usage captured from the Chat Completions stream."""
        get_usage = getattr(self._text, "get_usage", None)
        return get_usage() if get_usage else None

    def build_result(
        self,
        *,
        message_id: str,
        chat_id: str,
        content_chunks: list[ContentChunk],
        created_at: datetime,
        gpt_request: dict[str, Any] | None = None,
        debug_info: dict[str, Any] | None = None,
    ) -> LanguageModelStreamResponse:
        text_state = self._text.get_text()
        tool_calls = self._tools.get_tool_calls() if self._tools else None

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

        return LanguageModelStreamResponse(
            message=message,
            tool_calls=tool_calls if tool_calls else None,
            usage=self.usage,
        )
