"""Unique SDK side effects for OpenAI Responses streams (text + code interpreter).

Consolidates behavior previously split across ``TextDeltaStreamPartHandler`` and
``ResponseCodeInterpreterCallStreamPartHandler`` into a single
:class:`ResponseStreamPersistenceProtocol` implementation for use with
:func:`~unique_toolkit.framework_utilities.openai.streaming.pipeline.run.run_responses_stream_pipeline`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import unique_sdk
from openai.types.responses import (
    ResponseCompletedEvent,
    ResponseStreamEvent,
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

from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    StreamingReplacerProtocol,
)


@dataclass
class CodeInterpreterLogState:
    """Per-call state for Unique ``MessageLog`` updates (not an OpenAI payload).

    Stream events expose ``item_id`` on each
    :class:`~openai.types.responses.response_code_interpreter_call_code_delta_event.ResponseCodeInterpreterCallCodeDeltaEvent`
    (and siblings); that string matches
    :attr:`ResponseCodeInterpreterToolCall.id
    <openai.types.responses.response_code_interpreter_tool_call.ResponseCodeInterpreterToolCall.id>`
    once the call is materialized on the response.

    OpenAI's :class:`~openai.types.responses.response_code_interpreter_tool_call.ResponseCodeInterpreterToolCall`
    carries ``status`` in ``in_progress`` | ``completed`` | … — we map stream semantics
    onto Unique log ``status`` / ``text`` ourselves. ``message_log_id`` only exists
    after :meth:`unique_sdk.MessageLog.create_async`.
    """

    message_log_id: str
    item_id: str
    status: Literal["RUNNING", "COMPLETED", "FAILED"]
    text: str


class ResponsesSdkPersistence:
    """Emits ``Message`` and ``MessageLog`` events for a Responses stream."""

    def __init__(
        self,
        unique_settings: UniqueSettings,
        *,
        replacers: list[StreamingReplacerProtocol],
    ) -> None:
        self._settings = unique_settings
        self._replacers = replacers
        self._full_text = ""
        self._code = ""
        self._item_id_to_log: dict[str, CodeInterpreterLogState] = {}

    def reset(self) -> None:
        self._full_text = ""
        self._code = ""
        self._item_id_to_log = {}

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

        if item_id not in self._item_id_to_log:
            text_update = "Code interpreter call started"
            message_log = await unique_sdk.MessageLog.create_async(
                user_id=self._settings.context.auth.user_id.get_secret_value(),
                company_id=self._settings.context.auth.company_id.get_secret_value(),
                **unique_sdk.MessageLog.CreateMessageLogParams(
                    messageId=chat.last_assistant_message_id,
                    text=text_update,
                    status="RUNNING",
                    order=0,
                ),
            )
            self._item_id_to_log[item_id] = CodeInterpreterLogState(
                item_id=item_id,
                message_log_id=message_log.id,
                status=status,
                text=text_update,
            )
            return

        item = self._item_id_to_log[item_id]
        if item.status != status:
            item.status = status
            item.text = text_update
            await unique_sdk.MessageLog.update_async(
                user_id=self._settings.context.auth.user_id.get_secret_value(),
                company_id=self._settings.context.auth.company_id.get_secret_value(),
                message_log_id=item.message_log_id,
                **unique_sdk.MessageLog.UpdateMessageLogParams(
                    text=text_update,
                    status=item.status,
                ),
            )

    async def on_stream_end(self) -> None:
        return

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
