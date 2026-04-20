"""Chat Completions stream event router — dispatches chunks to typed handlers and builds the final result."""

from __future__ import annotations

from typing import TYPE_CHECKING

from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.language_model.schemas import LanguageModelStreamResponse

from ..protocols import StreamHandlerProtocol

if TYPE_CHECKING:
    from datetime import datetime

    from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

    from unique_toolkit._common.event_bus import TypedEventBus

    from ..protocols import (
        ChatCompletionTextHandlerProtocol,
        ChatCompletionToolCallHandlerProtocol,
        TextFlushed,
    )


class ChatCompletionStreamEventRouter:
    """Dispatches ``ChatCompletionChunk`` to typed handlers and materialises the result.

    Unlike the Responses router where event types are distinct, a single
    ``ChatCompletionChunk`` can carry both content and tool call deltas,
    so both handlers receive every chunk (a **broadcast** dispatch) and
    each handler inspects the chunk internally.

    Responsibilities (by design, small and disjoint):

    * **Dispatch (broadcast)** — every ``ChatCompletionChunk`` is sent to
      the text handler and, if attached, the tool-call handler.
    * **Lifecycle fan-out** — ``reset()`` / ``on_stream_end()`` iterate
      every attached handler.
    * **Bus re-export** — ``text_bus`` is re-exposed so the orchestrator
      can adapt inner-bus flushes into outer :class:`TextDelta` events.
    * **Result aggregation** — ``get_text()`` / ``build_result(...)``
      pull accumulated state from handlers and shape the toolkit result.

    Side-effects (``unique_sdk.Message.modify_async`` for references,
    timestamps, completion) are published as :data:`StreamEvent` on the
    bus owned by the orchestrator. This class is a **router + facade**
    over stateful handlers — no SDK, no settings, no bus of its own.
    """

    def __init__(
        self,
        *,
        text_handler: ChatCompletionTextHandlerProtocol,
        tool_call_handler: ChatCompletionToolCallHandlerProtocol | None = None,
    ) -> None:
        self._text = text_handler
        self._tools = tool_call_handler

    @property
    def _all_handlers(self) -> list[StreamHandlerProtocol]:
        return [h for h in (self._text, self._tools) if h is not None]

    @property
    def text_bus(self) -> TypedEventBus[TextFlushed]:
        """Re-expose the text handler's flush bus for orchestrator subscription.

        Subscribers (typically the orchestrator) attach once at construction
        and receive a :class:`TextFlushed` on every flush boundary crossed
        during streaming — no explicit drain/pull required.
        """
        return self._text.text_bus

    def reset(self) -> None:
        for h in self._all_handlers:
            h.reset()

    async def on_event(self, event: ChatCompletionChunk, *, index: int) -> None:
        """Dispatch one chunk to text + tool handlers.

        Text flushes are published on the text handler's
        :attr:`text_bus`; the tool handler has no per-event
        side-effect surface (final tool calls are read at stream end).
        """
        await self._text.on_chunk(event, index=index)
        if self._tools:
            await self._tools.on_chunk(event)

    async def on_stream_end(self) -> None:
        """Finalize all handlers.

        Any residual replacer text produces a final :class:`TextFlushed`
        on the text handler's bus before the orchestrator publishes
        :class:`StreamEnded`.
        """
        await self._text.on_stream_end()
        if self._tools:
            await self._tools.on_stream_end()

    def get_text(self):
        """Expose the text handler's accumulated state for orchestrator publishing."""
        return self._text.get_text()

    def build_result(
        self,
        *,
        message_id: str,
        chat_id: str,
        created_at: datetime,
    ) -> LanguageModelStreamResponse:
        text_state = self._text.get_text()
        tool_calls = self._tools.get_tool_calls() if self._tools else None

        message = ChatMessage(
            id=message_id,
            chat_id=chat_id,
            role=ChatMessageRole.ASSISTANT,
            text=text_state.full_text,
            created_at=created_at,
        )

        return LanguageModelStreamResponse(
            message=message,
            tool_calls=tool_calls if tool_calls else None,
        )
