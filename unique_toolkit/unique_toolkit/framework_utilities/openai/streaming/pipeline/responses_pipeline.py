"""Responses stream pipeline — routes events to typed handlers and builds the final result."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from openai.types.responses import (
    ResponseCompletedEvent,
    ResponseFunctionCallArgumentsDoneEvent,
    ResponseOutputItemAddedEvent,
    ResponseTextDeltaEvent,
)

from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.language_model.schemas import ResponsesLanguageModelStreamResponse

from .protocols import StreamHandlerProtocol

if TYPE_CHECKING:
    from openai.types.responses import ResponseStreamEvent

    from .protocols import (
        ResponsesCodeInterpreterHandlerProtocol,
        ResponsesCompletedHandlerProtocol,
        ResponsesTextDeltaHandlerProtocol,
        ResponsesToolCallHandlerProtocol,
    )


class ResponsesStreamPipeline:
    """Routes ``ResponseStreamEvent`` to typed handlers and materialises the result.

    Each handler is a typed protocol slot. The pipeline dispatches events by
    ``isinstance`` checks and delegates lifecycle calls (``reset``, ``on_stream_end``)
    to all registered handlers.
    """

    def __init__(
        self,
        *,
        text_handler: ResponsesTextDeltaHandlerProtocol,
        tool_call_handler: ResponsesToolCallHandlerProtocol | None = None,
        completed_handler: ResponsesCompletedHandlerProtocol | None = None,
        code_interpreter_handler: ResponsesCodeInterpreterHandlerProtocol | None = None,
    ) -> None:
        self._text = text_handler
        self._tools = tool_call_handler
        self._completed = completed_handler
        self._ci = code_interpreter_handler

    @property
    def _all_handlers(self) -> list[StreamHandlerProtocol]:
        return [
            h
            for h in (self._text, self._tools, self._completed, self._ci)
            if h is not None
        ]

    def reset(self) -> None:
        for h in self._all_handlers:
            h.reset()

    async def on_event(self, event: ResponseStreamEvent) -> None:
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
            await self._ci.on_code_interpreter_event(event)  # type: ignore[arg-type]
            return

    async def on_stream_end(self) -> None:
        for h in self._all_handlers:
            await h.on_stream_end()

    def build_result(
        self,
        *,
        message_id: str,
        chat_id: str,
        created_at: datetime,
    ) -> ResponsesLanguageModelStreamResponse:
        full_text, original_text = self._text.get_text()
        tool_calls = self._tools.get_tool_calls() if self._tools else None
        usage = self._completed.get_usage() if self._completed else None
        output = self._completed.get_output() if self._completed else []

        message = ChatMessage(
            id=message_id,
            chat_id=chat_id,
            role=ChatMessageRole.ASSISTANT,
            text=full_text,
            original_text=original_text,
            created_at=created_at,
        )

        return ResponsesLanguageModelStreamResponse(
            message=message,
            tool_calls=tool_calls if tool_calls else None,
            usage=usage,
            output=output,
        )


def _is_code_interpreter_event(event: ResponseStreamEvent) -> bool:
    from .responses_code_interpreter_handler import CodeInterpreterCallEvent

    return isinstance(event, CodeInterpreterCallEvent)
