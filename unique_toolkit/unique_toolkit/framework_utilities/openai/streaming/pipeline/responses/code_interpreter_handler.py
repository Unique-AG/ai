"""Handler for code interpreter call events — manages ``MessageLog`` lifecycle."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import unique_sdk
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

if TYPE_CHECKING:
    from unique_toolkit.app.unique_settings import UniqueSettings

CodeInterpreterCallEvent = (
    ResponseCodeInterpreterCallCodeDoneEvent
    | ResponseCodeInterpreterCallCompletedEvent
    | ResponseCodeInterpreterCallCodeDeltaEvent
    | ResponseCodeInterpreterCallInProgressEvent
    | ResponseCodeInterpreterCallInterpretingEvent
)


class ResponsesCodeInterpreterHandler:
    """Creates and updates ``MessageLog`` entries for code interpreter calls.

    Private state: ``_message_logs`` (dict mapping ``item_id`` to SDK ``MessageLog``),
    ``_code`` (accumulated code text).

    Side effects only — no contribution to the final ``LanguageModelStreamResponse``.
    """

    def __init__(self, settings: UniqueSettings) -> None:
        self._settings = settings
        self._message_logs: dict[str, unique_sdk.MessageLog] = {}
        self._code = ""

    async def on_code_interpreter_event(self, event: CodeInterpreterCallEvent) -> None:
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

    async def on_stream_end(self) -> None:
        if self._code:
            assert self._settings.context.chat is not None, (
                "Chat is required to retrieve the message"
            )
            message = unique_sdk.Message.retrieve(
                id=self._settings.context.chat.last_assistant_message_id,
                company_id=self._settings.context.auth.company_id.get_secret_value(),
                user_id=self._settings.context.auth.user_id.get_secret_value(),
                **unique_sdk.Message.RetrieveParams(
                    chatId=self._settings.context.chat.chat_id,
                ),
            )

            await unique_sdk.Message.modify_async(
                id=self._settings.context.chat.last_assistant_message_id,
                company_id=self._settings.context.auth.company_id.get_secret_value(),
                user_id=self._settings.context.auth.user_id.get_secret_value(),
                **unique_sdk.Message.ModifyParams(
                    chatId=self._settings.context.chat.chat_id,
                    text=(message.text or "")
                    + "\n used the following code to generate the response: ```\n"
                    + self._code
                    + "\n```",
                ),
            )

    def reset(self) -> None:
        self._message_logs = {}
        self._code = ""
