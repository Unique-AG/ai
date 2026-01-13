from unique_toolkit import ChatService
from unique_toolkit.chat.schemas import MessageExecutionUpdateStatus

EXECUTION_OPTIONS = {"toolChoices": ["SWOT"]}


class ProgressNotifier:
    def __init__(self, chat_service: ChatService, company_name: str):
        self._chat_service = chat_service
        self._company_name = company_name
        self._message_execution = None

    async def start(self):
        self._message_execution = (
            await self._chat_service.create_message_execution_async(
                message_id=self._chat_service.assistant_message_id,
                is_queueable=False,
                execution_options=EXECUTION_OPTIONS,
                progress_title=f"Starting SWOT Analysis for '{self._company_name}'",
                percentage_completed=0,
            )
        )

    async def update(self, *, progress: int | float, progress_title: str | None):
        await self._chat_service.update_message_execution_async(
            message_id=self._chat_service.assistant_message_id,
            percentage_completed=self._bound_and_convert_to_int(progress),
            progress_title=progress_title,
        )

    async def finish(self, failed: bool = False):
        if self._message_execution:
            await self._chat_service.update_message_execution_async(
                message_id=self._chat_service.assistant_message_id,
                percentage_completed=100,
                status=MessageExecutionUpdateStatus.COMPLETED
                if not failed
                else MessageExecutionUpdateStatus.FAILED,
            )

    @staticmethod
    def _bound_and_convert_to_int(progress: int | float) -> int:
        return int(max(0, min(progress, 100)))
