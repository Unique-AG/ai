from pydantic import Field

from unique_toolkit.agentic.tools.schemas import BaseToolConfig


class TodoConfig(BaseToolConfig):
    memory_key: str = Field(
        default="agent_todo_state",
        description="ShortTermMemory key under which TODO state is stored.",
    )
    max_todos: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Maximum number of TODO items to store.",
    )
