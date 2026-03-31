"""Chat Completions stream pipeline — routes chunks to typed handlers and builds the final result."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import unique_sdk

from unique_toolkit.app.unique_settings import UniqueSettings
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
        settings: UniqueSettings,
        text_handler: ChatCompletionTextHandlerProtocol,
        tool_call_handler: ChatCompletionToolCallHandlerProtocol | None = None,
    ) -> None:
        self._settings = settings
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

        if self._settings.context.chat is None:
            raise ValueError("Chat is not set")

        # CompletedAt must be set here so
        await unique_sdk.Message.modify_async(
            user_id=self._settings.context.auth.user_id.get_secret_value(),
            company_id=self._settings.context.auth.company_id.get_secret_value(),
            id=self._settings.context.chat.last_assistant_message_id,
            chatId=self._settings.context.chat.chat_id,
            completedAt=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),  # type: ignore
        )

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
