from typing import override

from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ToolProgressReporterProtocol,
)
from unique_toolkit.agentic.tools.tool_progress_reporter.base import ProgressState
from unique_toolkit.chat.schemas import MessageLogStatus
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
)


class MessageLogToolProgressReporter(ToolProgressReporterProtocol):
    def __init__(self, message_step_logger: MessageStepLogger) -> None:
        self._message_step_logger = message_step_logger
        self._active_message_logs = {}

    @override
    async def notify_from_tool_call(
        self,
        tool_call: LanguageModelFunction,
        name: str,
        message: str,
        state: ProgressState,
        references: list[ContentReference] | None = None,
    ) -> None:
        active_message_log = self._active_message_logs.get(tool_call.id)

        self._active_message_logs[tool_call.id] = (
            self._message_step_logger.create_or_update_message_log(
                active_message_log=active_message_log,
                header=name,
                progress_message=_italicize_message(message),
                status=_state_to_message_log_status(state),
                references=references,
            )
        )


def _italicize_message(message: str) -> str:
    return f"_{message}_"


def _state_to_message_log_status(state: ProgressState) -> MessageLogStatus:
    match state:
        case ProgressState.STARTED:
            return MessageLogStatus.RUNNING
        case ProgressState.RUNNING:
            return MessageLogStatus.RUNNING
        case ProgressState.FAILED:
            return MessageLogStatus.FAILED
        case ProgressState.FINISHED:
            return MessageLogStatus.COMPLETED
