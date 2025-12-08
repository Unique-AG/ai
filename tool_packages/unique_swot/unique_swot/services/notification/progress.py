from logging import getLogger

from unique_toolkit import ChatService

_LOGGER = getLogger(__name__)

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
        self._total_steps = 0

    def set_total_steps(self, total_steps: int):
        self._total_steps = total_steps

    async def start(self, session_info: str):
        self._session_info = session_info
        progress_bar = _PROGRESS_TEMPLATE.format(
            session_info=self._session_info,
            emoji="⚪️",
            percentage=0,
            bar=_get_string_progress_bar(0),
            info="Starting...",
        )
        await self._chat_service.modify_assistant_message_async(progress_bar)

    async def update(self, step_increment: float, progress_info: str):
        self._executed_fraction += step_increment

        percentage = _calculate_percentage_completed(
            self._executed_fraction, self._total_steps
        )
        progress_bar = _PROGRESS_TEMPLATE.format(
            session_info=self._session_info,
            emoji="🟡",
            percentage=percentage,
            bar=_get_string_progress_bar(percentage),
            info=progress_info,
        )
        await self._chat_service.modify_assistant_message_async(progress_bar)

    async def end(self, failed: bool = False, failure_message: str | None = None):
        progress_bar = _PROGRESS_TEMPLATE.format(
            session_info=self._session_info,
            emoji="🟢" if not failed else "🔴",
            percentage=100,
            bar=_get_string_progress_bar(100),
            info="Completed!" if not failed else failure_message,
        )
        await self._chat_service.modify_assistant_message_async(
            progress_bar, set_completed_at=True
        )


def _get_string_progress_bar(percentage: int) -> str:
    max_characters = 33

    num_full_blocks = max_characters * percentage // 100
    num_empty_blocks = max_characters - num_full_blocks
    return "█" * num_full_blocks + "░" * num_empty_blocks


def _calculate_percentage_completed(current_step: float, total_steps: float) -> int:
    if total_steps == 0:
        return 0

    percentage = int(current_step / total_steps * 100)
    if percentage > 100 or percentage < 0:
        _LOGGER.error(
            f"Percentage completed is out of range: {percentage}. Must be between 0 and 100. Check your code!"
        )
        percentage = _clamp(percentage, 0, 100)
    return percentage


def _clamp(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(value, max_value))
