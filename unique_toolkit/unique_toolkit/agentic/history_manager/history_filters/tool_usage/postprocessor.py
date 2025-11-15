from typing import Callable, override

from pydantic import RootModel

from unique_toolkit.agentic.postprocessor.postprocessor_manager import Postprocessor
from unique_toolkit.agentic.short_term_memory_manager.persistent_short_term_memory_manager import (
    PersistentShortMemoryManager,
)
from unique_toolkit.language_model import (
    LanguageModelStreamResponse,
)
from unique_toolkit.short_term_memory import ShortTermMemoryService


class SaveToolCallsPostprocessor(Postprocessor):
    """
    Save names of tools called by the model in short-term memory.
    It uses message-level short-term memory to store unique tool call names used by the model.
    """

    def __init__(
        self,
        company_id: str,
        user_id: str,
        get_tool_calls: Callable[[], list[str]],
    ) -> None:
        super().__init__(self.__class__.__name__)
        self._get_tool_calls = get_tool_calls
        self._company_id = company_id
        self._user_id = user_id

    @override
    async def run(self, loop_response: LanguageModelStreamResponse) -> None:
        short_term_memory_manager = _get_short_term_memory_manager(
            company_id=self._company_id,
            user_id=self._user_id,
            assistant_message_id=loop_response.message.id,
        )

        await short_term_memory_manager.save_async(
            _ToolCallsShortTermMemorySchema(set(self._get_tool_calls()))
        )

    @override
    def apply_postprocessing_to_response(
        self, loop_response: LanguageModelStreamResponse
    ) -> bool:
        return False

    @override
    async def remove_from_text(self, text: str) -> str:
        return text

    @classmethod
    async def get_assistant_message_used_tool_calls(
        cls, company_id: str, user_id: str, assistant_message_id: str
    ) -> set[str] | None:
        """
        Retrieves the names of tools called by the model from short-term memory.
        A None value indicates that the tool calls used are unknown.
        """
        short_term_memory_manager = _get_short_term_memory_manager(
            company_id=company_id,
            user_id=user_id,
            assistant_message_id=assistant_message_id,
        )

        tool_calls = await short_term_memory_manager.load_async()

        if tool_calls is None:
            return None

        return tool_calls.root


_TOOL_CALLS_SHORT_TERM_MEMORY_KEY = "assistant_message_used_tool_calls"
_ToolCallsShortTermMemorySchema = RootModel[set[str]]


def _get_short_term_memory_manager(
    company_id: str,
    user_id: str,
    assistant_message_id: str,
) -> PersistentShortMemoryManager[_ToolCallsShortTermMemorySchema]:
    short_term_memory_service = ShortTermMemoryService(
        user_id=user_id,
        company_id=company_id,
        chat_id=None,
        message_id=assistant_message_id,  # Attach memory to the assistant message
    )
    return PersistentShortMemoryManager(
        short_term_memory_service=short_term_memory_service,
        short_term_memory_schema=_ToolCallsShortTermMemorySchema,
        short_term_memory_name=_TOOL_CALLS_SHORT_TERM_MEMORY_KEY,
    )
