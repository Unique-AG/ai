from openai import BaseModel

from unique_toolkit import ShortTermMemoryService
from unique_toolkit.agentic.short_term_memory_manager.persistent_short_term_memory_manager import (
    PersistentShortMemoryManager,
)

SHORT_TERM_MEMORY_NAME = "container_code_execution"


class CodeExecutionShortTermMemorySchema(BaseModel):
    container_id: str
    file_paths: dict[str, str] = {}


CodeExecutionMemoryManager = PersistentShortMemoryManager[
    CodeExecutionShortTermMemorySchema
]


def get_container_code_execution_short_term_memory_manager(
    company_id: str, user_id: str, chat_id: str
) -> CodeExecutionMemoryManager:
    short_term_memory_service = ShortTermMemoryService(
        company_id=company_id,
        user_id=user_id,
        chat_id=chat_id,
        message_id=None,
    )
    short_term_memory_manager = PersistentShortMemoryManager(
        short_term_memory_service=short_term_memory_service,
        short_term_memory_schema=CodeExecutionShortTermMemorySchema,
        short_term_memory_name=SHORT_TERM_MEMORY_NAME,
    )
    return short_term_memory_manager
