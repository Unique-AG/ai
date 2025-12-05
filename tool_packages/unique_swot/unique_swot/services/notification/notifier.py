from logging import getLogger

from unique_toolkit import ChatService
from unique_toolkit.content.schemas import ContentReference

from unique_swot.services.notification.log_registry import LogRegistry
from unique_swot.services.notification.progress import ProgressBar

_LOGGER = getLogger(__name__)


class Notifier:
    def __init__(self, chat_service: ChatService, message_id: str):
        self._chat_service = chat_service
        self._message_id = message_id
        self._log_registry = LogRegistry()
        self._progress_bar = ProgressBar(chat_service=chat_service)

    def set_progress_total_steps(self, total_steps: int):
        self._progress_bar.set_total_steps(total_steps=total_steps)

    async def init_progress(self, session_info: str):
        await self._progress_bar.start(session_info=session_info)

    async def increment_progress(self, step_increment: float, progress_info: str):
        await self._progress_bar.update(
            step_increment=step_increment, progress_info=progress_info
        )

    async def end_progress(
        self, failed: bool = False, failure_message: str | None = None
    ):
        await self._progress_bar.end(failed=failed, failure_message=failure_message)

    async def notify(
        self, title: str, description: str = "", sources: list[ContentReference] = []
    ):
        await self._log_registry.add(
            chat_service=self._chat_service,
            message_id=self._message_id,
            title=title,
            description=description,
            sources=sources,
        )
