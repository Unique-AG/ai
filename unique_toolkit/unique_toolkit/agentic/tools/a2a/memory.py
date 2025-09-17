from unique_toolkit import ShortTermMemoryService
from unique_toolkit.agentic.short_term_memory_manager.persistent_short_term_memory_manager import (
    PersistentShortMemoryManager,
)
from unique_toolkit.agentic.tools.a2a.schema import SubAgentShortTermMemorySchema


def _get_short_term_memory_name(assistant_id: str) -> str:
    return f"sub_agent_chat_id_{assistant_id}"


def get_sub_agent_short_term_memory_manager(
    company_id: str, user_id: str, chat_id: str, assistant_id: str
) -> PersistentShortMemoryManager[SubAgentShortTermMemorySchema]:
    short_term_memory_service = ShortTermMemoryService(
        company_id=company_id,
        user_id=user_id,
        chat_id=chat_id,
        message_id=None,
    )
    short_term_memory_manager = PersistentShortMemoryManager(
        short_term_memory_service=short_term_memory_service,
        short_term_memory_schema=SubAgentShortTermMemorySchema,
        short_term_memory_name=_get_short_term_memory_name(assistant_id),
    )
    return short_term_memory_manager
