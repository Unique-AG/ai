from logging import getLogger

from unique_toolkit import ChatService
from unique_toolkit.content.schemas import ContentReference

from unique_swot.services.notification.log_registry import LogRegistry

_LOGGER = getLogger(__name__)


class StepNotifier:
    def __init__(self, chat_service: ChatService):
        self._chat_service = chat_service
        self._log_registry = LogRegistry()
        self._message_execution = None

    async def notify(
        self,
        title: str,
        description: str = "",
        sources: list[ContentReference] = [],
        progress: int | None = None,
        completed: bool = False,
    ):
        await self._log_registry.add(
            chat_service=self._chat_service,
            message_id=self._chat_service.assistant_message_id,
            title=title,
            progress=progress,
            description=description,
            sources=sources,
            completed=completed,
        )

    def get_total_number_of_references(self) -> int:
        return self._log_registry._total_number_of_references
