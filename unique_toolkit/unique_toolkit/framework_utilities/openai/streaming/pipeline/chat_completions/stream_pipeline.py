"""Chat Completions stream pipeline — routes chunks to typed handlers and builds the final result."""

from __future__ import annotations

from typing import TYPE_CHECKING

from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.language_model.schemas import LanguageModelStreamResponse

from ..protocols import StreamHandlerProtocol

if TYPE_CHECKING:
    from datetime import datetime

    from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

    from ..protocols import (
        ChatCompletionTextHandlerProtocol,
        ChatCompletionToolCallHandlerProtocol,
    )


class ChatCompletionStreamPipeline:
    """Routes ``ChatCompletionChunk`` to typed handlers and materialises the result.

    Unlike the Responses pipeline where event types are distinct, a single
    ``ChatCompletionChunk`` can carry both content and tool call deltas,
    so both handlers receive every chunk and inspect it internally.

    Side-effects (``unique_sdk.Message.modify_async`` for references,
    timestamps, completion) are published as :data:`StreamEvent` on the
    bus owned by the orchestrator. This class is purely a dispatcher over
    stateful handlers — no SDK, no settings, no bus.
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

    def reset(self) -> None:
        for h in self._all_handlers:
            h.reset()

    async def on_event(self, event: ChatCompletionChunk, *, index: int) -> bool:
        """Dispatch one chunk to text + tool handlers.

        Returns:
            True if the text handler signalled a flush boundary this chunk,
            indicating the caller should observe the updated text and
            publish a :class:`TextDelta` event.
        """
        flush = await self._text.on_chunk(event, index=index)
        if self._tools:
            await self._tools.on_chunk(event)
        return flush

    async def on_stream_end(self) -> bool:
        """Finalize all handlers.

        Returns:
            True if the text handler produced a residual flush (buffered
            replacer output) that should be observed before the final
            :class:`StreamEnded` event is published.
        """
        flushed = await self._text.on_stream_end()
        if self._tools:
            await self._tools.on_stream_end()
        return flushed

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
