from logging import getLogger
from typing import Self

from pydantic import BaseModel
from unique_toolkit import ChatService
from unique_toolkit.chat.schemas import (
    MessageLogDetails,
    MessageLogEvent,
    MessageLogStatus,
    MessageLogUncitedReferences,
)

from unique_swot.services.session import SwotAnalysisSessionConfig

_LOGGER = getLogger(__name__)


class MessageLogRegistry(BaseModel):
    text: str
    message_log_id: str
    order: int
    status: MessageLogStatus
    message_log_events: list[MessageLogEvent]

    @classmethod
    def create(
        cls,
        chat_service: ChatService,
        message_id: str,
        notification_title: str,
        order: int,
        status: MessageLogStatus,
        message_log_event: MessageLogEvent | None = None,
    ) -> Self:
        if message_log_event is not None:
            data = [message_log_event]
        else:
            data = []
        details = MessageLogDetails(data=data)
        message_log = chat_service.create_message_log(
            message_id=message_id,
            text=notification_title,
            status=status,
            order=order,
            details=details,
            uncited_references=MessageLogUncitedReferences(data=[]),
            references=[],
        )
        assert message_log.message_log_id is not None

        return cls(
            text=notification_title,
            message_log_id=message_log.message_log_id,
            order=order,
            status=status,
            message_log_events=data,
        )

    def update(
        self,
        chat_service: ChatService,
        status: MessageLogStatus,
        message_log_event: MessageLogEvent | None = None,
    ) -> Self:
        self.status = status
        if message_log_event is not None:
            self.message_log_events.append(message_log_event)
        details = MessageLogDetails(data=self.message_log_events)
        chat_service.update_message_log(
            message_log_id=self.message_log_id,
            text=self.text,
            order=self.order,
            status=self.status,
            details=details,
            uncited_references=MessageLogUncitedReferences(data=[]),
            references=[],
        )
        return self


class ProgressNotifier:
    def __init__(self, chat_service: ChatService, message_id: str):
        self._progress_bar = ProgressBar(chat_service=chat_service)
        self._chat_service = chat_service
        self._execution_registery: dict[str, MessageLogRegistry] = {}
        self._message_id = message_id
        self._order = 0

    def start_progress(
        self, total_steps: int, session_config: SwotAnalysisSessionConfig
    ):
        _LOGGER.info(f"Starting progress with total steps: {total_steps}")
        self._progress_bar.start(
            session_info=session_config.render_session_info(),
            total_steps=total_steps,
        )

    def update_progress(
        self,
        step_precentage_increment: float,
        current_step_message: str,
    ):
        self._progress_bar.update(
            step_increment=step_precentage_increment, info=current_step_message
        )

    def notify(
        self,
        notification_title: str,
        status: MessageLogStatus,
        message_log_event: MessageLogEvent | None = None,
    ):
        _LOGGER.info(f"Notifying: {notification_title} with status: {status}")
        if message_log_event is not None:
            _LOGGER.info(f"Message log event: {message_log_event}")
        self._add_message_log(
            notification_title=f"**{notification_title}**",
            message_log_event=message_log_event,
            status=status,
        )

    def _add_message_log(
        self,
        notification_title: str,
        status: MessageLogStatus,
        message_log_event: MessageLogEvent | None = None,
    ):
        key = notification_title
        if key not in self._execution_registery:
            self._execution_registery[key] = MessageLogRegistry.create(
                chat_service=self._chat_service,
                message_id=self._message_id,
                notification_title=notification_title,
                order=self._order,
                status=status,
                message_log_event=message_log_event,
            )
            self._order += 1
        else:
            self._execution_registery[key].update(
                chat_service=self._chat_service,
                status=status,
                message_log_event=message_log_event,
            )

    def end_progress(self, failed: bool, failure_message: str | None = None):
        if failed:
            _LOGGER.info(
                f"Ending progress with failed: {failed} and failure message: {failure_message}"
            )
            self._progress_bar.done(failed=True, failure_message=failure_message)
        else:
            self._progress_bar.done(failed=False)


_PROGRESS_TEMPLATE = """
{session_info}

{emoji} {bar} {percentage}%
_{info}_
"""


class ProgressBar:
    def __init__(self, chat_service: ChatService):
        self._chat_service = chat_service
        self._executed_fraction = 0
        self._session_info = ""
        self._total_steps = 90

    def start(self, session_info: str, total_steps: int):
        self._session_info = session_info
        self._total_steps = total_steps
        progress_bar = _PROGRESS_TEMPLATE.format(
            session_info=self._session_info,
            emoji="⚪️",
            percentage=0,
            bar=self._get_string_progress_bar(0),
            info="Starting...",
        )
        self._chat_service.modify_assistant_message(progress_bar)

    def update(self, step_increment: float, info: str):
        self._executed_fraction += step_increment

        percentage = self._calculate_percentage_completed(
            self._executed_fraction, self._total_steps
        )
        progress_bar = _PROGRESS_TEMPLATE.format(
            session_info=self._session_info,
            emoji="🟡",
            percentage=percentage,
            bar=self._get_string_progress_bar(percentage),
            info=info,
        )
        self._chat_service.modify_assistant_message(progress_bar)

    def done(self, failed: bool = False, failure_message: str | None = None):
        progress_bar = _PROGRESS_TEMPLATE.format(
            session_info=self._session_info,
            emoji="🟢" if not failed else "🔴",
            percentage=100,
            bar=self._get_string_progress_bar(100),
            info="Completed!" if not failed else failure_message,
        )
        self._chat_service.modify_assistant_message(progress_bar, set_completed_at=True)

    @staticmethod
    def _get_string_progress_bar(percentage: int) -> str:
        max_characters = 33

        num_full_blocks = max_characters * percentage // 100
        num_empty_blocks = max_characters - num_full_blocks
        return "█" * num_full_blocks + "░" * num_empty_blocks

    @staticmethod
    def _calculate_percentage_completed(current_step: float, total_steps: float) -> int:
        percentage = int(current_step / total_steps * 100)
        if percentage > 100 or percentage < 0:
            _LOGGER.error(
                f"Percentage completed is out of range: {percentage}. Must be between 0 and 100. Check your code!"
            )
            percentage = _clamp(percentage, 0, 100)
        return percentage


def _clamp(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(value, max_value))
