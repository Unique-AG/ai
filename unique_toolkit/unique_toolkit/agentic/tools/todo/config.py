from pydantic import Field

from unique_toolkit.agentic.tools.schemas import BaseToolConfig


class TodoConfig(BaseToolConfig):
    # Default must match unique_orchestrator.config.TodoTrackingConfig.memory_key
    memory_key: str = Field(
        default="agent_todo_state",
        description="ShortTermMemory key under which TODO state is stored.",
    )
