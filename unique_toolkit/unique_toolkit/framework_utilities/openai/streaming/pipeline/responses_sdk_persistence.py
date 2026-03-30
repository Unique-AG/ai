"""Unique SDK side effects for OpenAI Responses streams (text + code interpreter).

Consolidates behavior previously split across ``TextDeltaStreamPartHandler`` and
``ResponseCodeInterpreterCallStreamPartHandler`` into a single
:class:`ResponseStreamPersistenceProtocol` implementation for use with
:func:`~unique_toolkit.framework_utilities.openai.streaming.pipeline.run.run_responses_stream_pipeline`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import unique_sdk
from openai.types.responses import (
    ResponseCompletedEvent,
    ResponseTextDeltaEvent,
)
from openai.types.responses.response_code_interpreter_call_code_delta_event import (
    ResponseCodeInterpreterCallCodeDeltaEvent,
)
from openai.types.responses.response_code_interpreter_call_code_done_event import (
    ResponseCodeInterpreterCallCodeDoneEvent,
)
from openai.types.responses.response_code_interpreter_call_completed_event import (
    ResponseCodeInterpreterCallCompletedEvent,
)
from openai.types.responses.response_code_interpreter_call_in_progress_event import (
    ResponseCodeInterpreterCallInProgressEvent,
)
from openai.types.responses.response_code_interpreter_call_interpreting_event import (
    ResponseCodeInterpreterCallInterpretingEvent,
)

from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    StreamingReplacerProtocol,
    chunks_to_sdk_references,
)

if TYPE_CHECKING:
    from openai.types.responses import ResponseStreamEvent

    from unique_toolkit.app.unique_settings import UniqueSettings
    from unique_toolkit.content.schemas import ContentChunk


CodeInterpreterCallEvent = (
    ResponseCodeInterpreterCallCodeDoneEvent
    | ResponseCodeInterpreterCallCompletedEvent
    | ResponseCodeInterpreterCallCodeDeltaEvent
    | ResponseCodeInterpreterCallInProgressEvent
    | ResponseCodeInterpreterCallInterpretingEvent
)


class ResponsesSdkPersistence:
    """Emits ``Message`` and ``MessageLog`` events for a Responses stream, and optionally
    persists the final normalized text + references via ``Message.modify_async`` at the
    end of the stream."""

    def __init__(
        self,
        unique_settings: UniqueSettings,
        *,
        replacers: list[StreamingReplacerProtocol],
        content_chunks: list[ContentChunk] | None = None,
        resolve_references: bool = False,
    ) -> None:
        self._settings = unique_settings
        self._replacers = replacers
        self._content_chunks = content_chunks
        self._resolve_references = resolve_references
        self._full_text = ""
        self._code = ""
        self._message_logs: dict[str, unique_sdk.MessageLog] = {}

    @property
    def full_text(self) -> str:
        """Normalized text accumulated across the stream (after replacers)."""
        return self._full_text

    def reset(self) -> None:
        self._full_text = ""
        self._code = ""
        self._message_logs = {}

    async def _handle_code_interpreter_call_event(
        self, event: CodeInterpreterCallEvent
    ) -> None:
        if isinstance(event, ResponseCodeInterpreterCallCodeDoneEvent):
            self._code = event.code
            text_update = "Code interpreter call completed"
            status: Literal["RUNNING", "COMPLETED", "FAILED"] = "COMPLETED"
        elif isinstance(event, ResponseCodeInterpreterCallCompletedEvent):
            text_update = "Code interpreter call completed"
            status = "COMPLETED"
        elif isinstance(event, ResponseCodeInterpreterCallCodeDeltaEvent):
            self._code += event.delta
            text_update = "Code interpreter call in progress"
            status = "RUNNING"
        elif isinstance(event, ResponseCodeInterpreterCallInProgressEvent):
            text_update = "Code interpreter call in progress"
            status = "RUNNING"
        elif isinstance(event, ResponseCodeInterpreterCallInterpretingEvent):
            text_update = "Code interpreter call interpreting"
            status = "RUNNING"
        else:
            return

        item_id = event.item_id
        chat = self._settings.context.chat
        assert chat is not None
        if item_id not in self._message_logs:
            self._message_logs[item_id] = await unique_sdk.MessageLog.create_async(
                user_id=self._settings.context.auth.user_id.get_secret_value(),
                company_id=self._settings.context.auth.company_id.get_secret_value(),
                **unique_sdk.MessageLog.CreateMessageLogParams(
                    messageId=chat.last_assistant_message_id,
                    text=text_update,
                    status=status,
                    order=0,
                ),
            )
            return

        log = self._message_logs[item_id]
        if log.status == status and log.text == text_update:
            return

        self._message_logs[item_id] = await unique_sdk.MessageLog.update_async(
            user_id=self._settings.context.auth.user_id.get_secret_value(),
            company_id=self._settings.context.auth.company_id.get_secret_value(),
            message_log_id=log.id,
            **unique_sdk.MessageLog.UpdateMessageLogParams(
                text=text_update,
                status=status,
            ),
        )

    async def on_event(
        self,
        event: ResponseStreamEvent,
        *,
        index: int,
    ) -> None:
        del index
        if self._settings.context.chat is None:
            return

        if isinstance(event, ResponseTextDeltaEvent):
            delta = event.delta
            for replacer in self._replacers:
                delta = replacer.process(delta)
            self._full_text += delta
            await self._emit_assistant_message_event()
            return

        if isinstance(event, ResponseCompletedEvent):
            await self._emit_assistant_message_event()
            return

        if isinstance(event, CodeInterpreterCallEvent):
            await self._handle_code_interpreter_call_event(event)
            return

    async def on_stream_end(self) -> None:
        # Cascade flush: each replacer's flush output is fed into the next replacer's
        # process() before that replacer is itself flushed.  This ensures the pattern
        # replacer's buffered tail reaches downstream replacers before they finalise.
        remaining = ""
        for replacer in self._replacers:
            if remaining:
                remaining = replacer.process(remaining)
            remaining += replacer.flush()
        if remaining:
            self._full_text += remaining
            if self._settings.context.chat is not None:
                await self._emit_assistant_message_event()

        if self._resolve_references and self._settings.context.chat is not None:
            await self._persist_final_message()

    async def _persist_final_message(self) -> None:
        """Write normalized text and references to the platform via ``Message.modify_async``."""
        chat = self._settings.context.chat
        assert chat is not None
        await unique_sdk.Message.modify_async(
            user_id=self._settings.context.auth.user_id.get_secret_value(),
            company_id=self._settings.context.auth.company_id.get_secret_value(),
            id=chat.last_assistant_message_id,
            chatId=chat.chat_id,
            text=self._full_text or None,
            references=chunks_to_sdk_references(self._content_chunks or []),
        )

    async def _emit_assistant_message_event(self) -> None:
        chat = self._settings.context.chat
        assert chat is not None
        await unique_sdk.Message.create_event_async(
            user_id=self._settings.context.auth.user_id.get_secret_value(),
            company_id=self._settings.context.auth.company_id.get_secret_value(),
            **unique_sdk.Message.CreateEventParams(
                chatId=chat.chat_id,
                messageId=chat.last_assistant_message_id,
                text=self._full_text,
            ),
        )
