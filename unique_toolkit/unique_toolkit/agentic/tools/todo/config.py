from pydantic import Field

from unique_toolkit.agentic.tools.schemas import BaseToolConfig


class TodoConfig(BaseToolConfig):
    """Configuration for the todo tracking tool.

    Prompt fields default to ``None``, which means the built-in prompts in
    ``service.py`` are used.  Set a non-``None`` value to override from the
    admin UI (via ``TodoTrackingConfig`` in the orchestrator).
    """

    memory_key: str = Field(
        default="agent_todo_state",
        description="ShortTermMemory key under which TODO state is stored.",
    )

    system_prompt: str | None = Field(
        default=None,
        description="Override the default system prompt injected for todo tracking. "
        "None uses the built-in default.",
    )

    execution_reminder: str | None = Field(
        default=None,
        description="Override the execution-phase reminder appended to tool responses. "
        "None uses the built-in default.",
    )
