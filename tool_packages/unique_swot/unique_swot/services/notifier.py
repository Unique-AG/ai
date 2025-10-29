from logging import getLogger
from typing import Self

from pydantic import BaseModel
from unique_toolkit import ChatService
from unique_toolkit.chat.schemas import (
    MessageExecutionType,
    MessageExecutionUpdateStatus,
    MessageLogDetails,
    MessageLogEvent,
    MessageLogStatus,
    MessageLogUncitedReferences,
)

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


def _calculate_percentage_completed(current_step: float, total_steps: float) -> int:
    return int(current_step / total_steps * 100)


class ProgressNotifier:
    def __init__(self, chat_service: ChatService, message_id: str):
        self._chat_service = chat_service
        self._execution_registery: dict[str, MessageLogRegistry] = {}
        self._message_id = message_id
        self._order = 0
        self._step_increment = 0

    def start_progress(self, total_steps: int):
        _LOGGER.info(f"Starting progress with total steps: {total_steps}")
        self._total_steps = total_steps

        self._chat_service.create_message_execution(
            message_id=self._message_id,
            type=MessageExecutionType.DEEP_RESEARCH,
            percentage_completed=0,
        )

    def update_progress(
        self,
        step_precentage_increment: float,
        seconds_remaining: int | None = None,
    ):
  
        self._step_increment += step_precentage_increment
        percentage_completed = _calculate_percentage_completed(
            self._step_increment, self._total_steps
        )
        if percentage_completed > 100:
            _LOGGER.warning(f"Percentage completed is greater than 100: {percentage_completed}. Maxing out at 100% to prevent error. Check your code!")
            percentage_completed = 100

        _LOGGER.info(f"Updating progress to: {percentage_completed}")
        self._chat_service.update_message_execution(
            message_id=self._message_id,
            percentage_completed=percentage_completed,
            seconds_remaining=seconds_remaining,
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
            notification_title=notification_title,
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

    def _update_progress(self, percentage_completed: int):
        _LOGGER.info(f"Updating progress to: {percentage_completed}")
        self._chat_service.update_message_execution(
            message_id=self._message_id,
            percentage_completed=percentage_completed,
        )

    def end_progress(self, success: bool = True):
        _LOGGER.info(f"Ending progress with success: {success}")
        status = (
            MessageExecutionUpdateStatus.COMPLETED
            if success
            else MessageExecutionUpdateStatus.FAILED
        )
        self._chat_service.update_message_execution(
            message_id=self._message_id,
            status=status,
            percentage_completed=100,
            seconds_remaining=0,
        )
