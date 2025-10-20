from abc import ABC, abstractmethod
from logging import getLogger
from typing import Any

from pydantic import BaseModel
from unique_toolkit import ChatService
from unique_toolkit.chat.schemas import (
    # MessageExecutionStatus,
    MessageExecutionType,
    # MessageExecutionUpdateStatus,
    # MessageLogDetails,
    # MessageLogEvent,
    MessageLogStatus,
)

_LOGGER = getLogger(__name__)


class StepRegistry(BaseModel):
    message_log_id: str
    status: MessageLogStatus
    details: str


def _calculate_percentage_completed(current_step: int, total_steps: int) -> int:
    return int((current_step + 1) / total_steps * 100)


class Notifier(ABC):
    @abstractmethod
    def notify(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError


class ProgressNotifier(Notifier):
    def __init__(self, chat_service: ChatService, message_id: str, total_steps: int):
        self._chat_service = chat_service
        self._total_steps = total_steps
        self._processed_steps = 0
        self._chat_service.create_message_execution(
            message_id=self._chat_service._assistant_message_id,
            type=MessageExecutionType.SWOT_ANALYSIS,
            percentage_completed=0,
        )

        self._execution_registery = {}

    @property
    def progress_precentage(self):
        return _calculate_percentage_completed(self._processed_steps, self._total_steps)

    # def notify(self, step_id, status: MessageLogStatus, details: str) -> None:
    #     self._execution_registery[step_id] = StepRegistry(
    #         status=status, details=details
    #     )

    #     self._chat_service.create_message_log(
    #         message_id=self._chat_service._assistant_message_id,
    #         text=f"Step {current_step} of {self._total_steps} completed",
    #         status=MessageLogStatus.RUNNING,
    #         order=current_step,
    #         details=MessageLogDetails(
    #             data=[
    #                 MessageLogEvent(
    #                     type="SWOTAnalysis",
    #                     text=details,
    #                 )
    #             ]
    #         ),
    #     )

    #     self._chat_service.update_message_execution(
    #         message_id=self._chat_service._assistant_message_id,
    #         status=MessageExecutionUpdateStatus.RUNNING,
    #         percentage_completed=percentage_completed,
    #     )

    # def _create_message_log(
    #     self, step_id: str, status: MessageLogStatus, details: str
    # ) -> None:
    #     message_log = self._chat_service.create_message_log(
    #         message_id=self._chat_service._assistant_message_id,
    #         text=f"Step {current_step} of {self._total_steps} completed",
    #         status=MessageLogStatus.RUNNING,
    #         order=current_step,
    #         details=MessageLogDetails(
    #             data=[
    #                 MessageLogEvent(
    #                     type="SWOTAnalysis",
    #                     text=details,
    #                 )
    #             ]
    #         ),
    #     )
    #     return StepRegistry(
    #         message_log_id=message_log.message_log_id, status=status, details=details
    #     )

    # def _update_message_execution(
    #     self,
    #     step_id: str,
    #     status: MessageExecutionUpdateStatus,
    #     percentage_completed: int,
    # ) -> None:
    #     self._chat_service.update_message_log(
    #         message_id=self._chat_service._assistant_message_id,
    #         status=status,
    #         percentage_completed=percentage_completed,
    #     )


class LoggerNotifier(Notifier):
    def notify(self, step_name: str, progress: float) -> None:
        _LOGGER.info(f"{step_name}: {progress}")
