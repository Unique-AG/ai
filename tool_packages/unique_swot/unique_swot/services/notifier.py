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
        message_log_event: MessageLogEvent,
    ) -> Self:
        message_log = chat_service.create_message_log(
            message_id=message_id,
            text=notification_title,
            status=status,
            order=order,
            details=MessageLogDetails(data=[message_log_event]),
            uncited_references=MessageLogUncitedReferences(data=[]),
            references=[],
        )
        assert message_log.message_log_id is not None

        return cls(
            text=notification_title,
            message_log_id=message_log.message_log_id,
            order=order,
            status=status,
            message_log_events=[message_log_event],
        )

    def update(
        self,
        chat_service: ChatService,
        status: MessageLogStatus,
        message_log_event: MessageLogEvent,
    ) -> Self:
        self.status = status
        self.message_log_events.append(message_log_event)
        chat_service.update_message_log(
            message_log_id=self.message_log_id,
            text=self.text,
            order=self.order,
            status=self.status,
            details=MessageLogDetails(data=self.message_log_events),
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
        self._total_steps = total_steps

        self._chat_service.create_message_execution(
            message_id=self._message_id,
            type=MessageExecutionType.DEEP_RESEARCH,
            percentage_completed=0,
        )

    def update_progress(
        self,
        step_precentage_increment: float | None = None,
        seconds_remaining: int | None = None,
    ):
        if seconds_remaining is None and step_precentage_increment is None:
            _LOGGER.warning(
                "No step increment or seconds remaining provided. Skipping progress update."
            )
            return

        percentage_completed = None
        if step_precentage_increment is not None:
            self._step_increment += step_precentage_increment
            percentage_completed = _calculate_percentage_completed(
                self._step_increment, self._total_steps
            )
            _LOGGER.info(f"Percentage completed: {percentage_completed}")

        self._chat_service.update_message_execution(
            message_id=self._message_id,
            status=MessageExecutionUpdateStatus.RUNNING,
            percentage_completed=percentage_completed,
            seconds_remaining=seconds_remaining,
        )

    def notify(
        self,
        notification_title: str,
        status: MessageLogStatus,
        message_log_event: MessageLogEvent,
    ):
        self._add_message_log(
            notification_title=notification_title,
            message_log_event=message_log_event,
            status=status,
        )

    def _add_message_log(
        self,
        notification_title: str,
        message_log_event: MessageLogEvent,
        status: MessageLogStatus,
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
        self._chat_service.update_message_execution(
            message_id=self._message_id,
            status=MessageExecutionUpdateStatus.RUNNING,
            percentage_completed=percentage_completed,
        )

    def end_progress(self, success: bool = True):
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
