from abc import ABC, abstractmethod
from logging import getLogger
from typing import Any

from pydantic import BaseModel
from unique_toolkit import ChatService
from unique_toolkit.chat.schemas import (
    MessageExecutionStatus,
    MessageExecutionType,
    MessageExecutionUpdateStatus,
    MessageLogDetails,
    MessageLogEvent,
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
    def __init__(self, chat_service: ChatService, message_id: str):
        self._chat_service = chat_service
        self._processed_steps = 0
        self._execution_registery = {}
        
    @property
    def progress_precentage(self):
        return _calculate_percentage_completed(self._processed_steps, self._total_steps)
    
    
    def start_progress(self, total_steps: int):
        self._total_steps = total_steps
        
        self._chat_service.create_message_execution(
            message_id=self._chat_service._assistant_message_id,
            type=MessageExecutionType.DEEP_RESEARCH,
            percentage_completed=0,
        )
        
    def notify(self, step_name: str, progress: float):
        self._chat_service.create_message_log(
            message_id=self._chat_service._assistant_message_id,
            text=f"{step_name}: {progress}",
            status=MessageLogStatus.RUNNING,
            order=0,
            details=MessageLogDetails(
                data=[
                    MessageLogEvent(
                        type="InternalSearch",
                        text=f"{step_name}: {progress}",
                    )
                ]
            ),
        )


    def end_progress(self):
        self._chat_service.update_message_execution(
            message_id=self._chat_service._assistant_message_id,
            status=MessageExecutionUpdateStatus.COMPLETED,
            percentage_completed=100,
        )

class LoggerNotifier(Notifier):
    def notify(self, step_name: str, progress: float) -> None:
        _LOGGER.info(f"{step_name}: {progress}")
