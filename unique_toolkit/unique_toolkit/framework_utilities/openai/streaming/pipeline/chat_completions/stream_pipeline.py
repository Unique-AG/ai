"""Chat Completions stream pipeline — routes chunks to typed handlers and builds the final result."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.language_model.schemas import LanguageModelStreamResponse

from ..protocols import StreamHandlerProtocol

if TYPE_CHECKING:
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

    async def on_event(self, event: ChatCompletionChunk, *, index: int) -> None:
        await self._text.on_chunk(event, index=index)
        if self._tools:
            await self._tools.on_chunk(event)

    async def on_stream_end(self) -> None:
        for h in self._all_handlers:
            await h.on_stream_end()

    def build_result(
        self,
        *,
        message_id: str,
        chat_id: str,
        created_at: datetime,
    ) -> LanguageModelStreamResponse:
        full_text, _original_text = self._text.get_text()
        tool_calls = self._tools.get_tool_calls() if self._tools else None

        message = ChatMessage(
            id=message_id,
            chat_id=chat_id,
            role=ChatMessageRole.ASSISTANT,
            text=full_text,
            created_at=created_at,
        )

        return LanguageModelStreamResponse(
            message=message,
            tool_calls=tool_calls if tool_calls else None,
        )
