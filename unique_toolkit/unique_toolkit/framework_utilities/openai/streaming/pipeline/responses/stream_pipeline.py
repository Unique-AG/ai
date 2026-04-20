"""Responses stream pipeline — routes events to typed handlers and builds the final result."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openai.types.responses import (
    ResponseCompletedEvent,
    ResponseFunctionCallArgumentsDoneEvent,
    ResponseOutputItemAddedEvent,
    ResponseTextDeltaEvent,
)

from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.language_model.schemas import ResponsesLanguageModelStreamResponse

from ..protocols import StreamHandlerProtocol
from ..protocols.common import (
    ActivityProgressProducer,
    ActivityProgressUpdate,
    AppendixProducer,
)

if TYPE_CHECKING:
    from datetime import datetime

    from openai.types.responses import ResponseStreamEvent

    from ..protocols import (
        ResponsesCodeInterpreterHandlerProtocol,
        ResponsesCompletedHandlerProtocol,
        ResponsesTextDeltaHandlerProtocol,
        ResponsesToolCallHandlerProtocol,
    )


class ResponsesStreamPipeline:
    """Routes ``ResponseStreamEvent`` to typed handlers and materialises the result.

    Side-effects (``unique_sdk.Message.modify_async``) are the concern of
    :data:`StreamEvent` subscribers on the bus owned by the orchestrator.
    This class is purely a dispatcher — no SDK, no settings, no bus.
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

    async def on_event(self, event: ResponseStreamEvent) -> bool:
        """Dispatch one event to the appropriate handler.

        Returns:
            True if this event produced observable text, indicating the
            caller should publish a :class:`TextDelta`. False for all
            non-text events (tool calls, completion, code interpreter).
        """
        if isinstance(event, ResponseTextDeltaEvent):
            return await self._text.on_text_delta(event)

        if isinstance(event, ResponseOutputItemAddedEvent) and self._tools:
            await self._tools.on_output_item_added(event)
            return False

        if isinstance(event, ResponseFunctionCallArgumentsDoneEvent) and self._tools:
            await self._tools.on_function_arguments_done(event)
            return False

        if isinstance(event, ResponseCompletedEvent) and self._completed:
            await self._completed.on_completed(event)
            return False

        if self._ci and _is_code_interpreter_event(event):
            await self._ci.on_code_interpreter_event(event)  # type: ignore[arg-type]
            return False

        return False

    async def on_stream_end(self) -> bool:
        """Finalize all handlers.

        Returns:
            True if the text handler produced a residual flush (buffered
            replacer output) that should be observed before the final
            :class:`StreamEnded` event is published.
        """
        flushed = await self._text.on_stream_end()
        for h in self._all_handlers:
            if h is self._text:
                continue
            await h.on_stream_end()
        return flushed

    def get_text(self):
        """Expose the text handler's accumulated state for orchestrator publishing."""
        return self._text.get_text()

    def drain_activity_progress(self) -> list[ActivityProgressUpdate]:
        """Return and clear progress updates collected from every handler.

        Iterates all registered handlers and asks each one conforming to
        :class:`ActivityProgressProducer` to drain its pending updates —
        no per-handler slot is hard-coded, so a new progress-producing
        handler plugs in simply by exposing ``drain_pending``.
        """
        updates: list[ActivityProgressUpdate] = []
        for handler in self._all_handlers:
            if isinstance(handler, ActivityProgressProducer):
                updates.extend(handler.drain_pending())
        return updates

    def get_appendices(self) -> tuple[str, ...]:
        """Collect assistant-message appendices contributed by handlers.

        Any handler conforming to :class:`AppendixProducer` can contribute
        text — the result is the ordered concatenation of non-``None``
        appendices. The orchestrator attaches the tuple to
        :class:`StreamEnded` so the message persister writes
        ``full_text + appendices`` in a single round-trip (avoiding a
        retrieve + modify dance).
        """
        appendices: list[str] = []
        for handler in self._all_handlers:
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
        created_at: datetime,
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
            created_at=created_at,
        )

        return ResponsesLanguageModelStreamResponse(
            message=message,
            tool_calls=tool_calls if tool_calls else None,
            usage=usage,
            output=output,
        )


def _is_code_interpreter_event(event: ResponseStreamEvent) -> bool:
    from .code_interpreter_handler import CodeInterpreterCallEvent

    return isinstance(event, CodeInterpreterCallEvent)
