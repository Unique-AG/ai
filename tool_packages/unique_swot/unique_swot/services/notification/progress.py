from unique_toolkit import ChatService
from unique_toolkit.chat.schemas import MessageExecutionUpdateStatus

EXECUTION_OPTIONS = {"toolChoices": ["SWOT"]}


class ProgressNotifier:
    def __init__(self, chat_service: ChatService, company_name: str):
        self._chat_service = chat_service
        self._company_name = company_name
        self._message_execution = None
        self._title = ""
        self._step_size = 0
        self._progress = 0

    @property
    def title(self) -> str:
        return self._title

    @property
    def step_size(self) -> int | float:
        return self._step_size

    @step_size.setter
    def step_size(self, value: int | float):
        self._step_size = value

    @property
    def progress(self) -> int:
        return self._progress

    @progress.setter
    def progress(self, value: int | float):
        value = self._bound_and_convert_to_int(value)
        self._progress = value

    async def start(self, *, title: str = ""):
        self._title = title
        self._message_execution = (
            await self._chat_service.create_message_execution_async(
                message_id=self._chat_service.assistant_message_id,
                is_queueable=False,
                execution_options=EXECUTION_OPTIONS,
                progress_title=self._title,
                percentage_completed=0,
            )
        )

    async def increment(self, fraction: float):
        self.progress += fraction * self._step_size
        await self._chat_service.update_message_execution_async(
            message_id=self._chat_service.assistant_message_id,
            percentage_completed=self.progress,
            progress_title=self._title,
        )

    async def update(self, *, progress: int | float, title: str | None = None):
        self.progress = progress
        if title:
            self._title = title

        await self._chat_service.update_message_execution_async(
            message_id=self._chat_service.assistant_message_id,
            percentage_completed=self._bound_and_convert_to_int(progress),
            progress_title=self._title,
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
