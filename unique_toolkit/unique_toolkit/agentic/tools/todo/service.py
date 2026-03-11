from __future__ import annotations

from logging import getLogger

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.short_term_memory_manager.persistent_short_term_memory_manager import (
    PersistentShortMemoryManager,
)
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.todo.config import TodoConfig
from unique_toolkit.agentic.tools.todo.schemas import (
    TodoItem,
    TodoState,
    TodoWriteInput,
)
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.language_model import LanguageModelToolDescription
from unique_toolkit.language_model.schemas import LanguageModelFunction
from unique_toolkit.short_term_memory.service import ShortTermMemoryService

logger = getLogger(__name__)

_STATUS_ICONS = {
    "pending": "[ ]",
    "in_progress": "[>]",
    "completed": "[x]",
    "cancelled": "[-]",
}

_TODO_SYSTEM_PROMPT = (
    "You have access to a task tracking system (todo_write, todo_read). "
    "Use it proactively for complex tasks with 3+ distinct steps.\n\n"
    "When to use:\n"
    "- Multi-step analysis or research tasks\n"
    "- Tasks requiring data from multiple sources\n"
    "- Any task where tracking progress helps avoid repeating work\n\n"
    "When NOT to use:\n"
    "- Simple single-step questions\n"
    "- Quick lookups or formatting tasks\n\n"
    "Mark only ONE item as in_progress at a time. "
    "Update status immediately after completing each step."
)


def _format_lines(state: TodoState) -> list[str]:
    return [
        f"  {_STATUS_ICONS.get(t.status, '[ ]')} {t.content} (id: {t.id})"
        for t in state.todos
    ]


def format_todo_state(state: TodoState) -> str:
    """Format TODO state as human-readable text for tool responses."""
    if not state.todos:
        return "No tasks tracked."

    summary = _summarize(state.todos)
    return f"Task list ({summary}):\n" + "\n".join(_format_lines(state))


def format_todo_system_reminder(state: TodoState) -> str:
    """Format TODO state as a <system-reminder> for injection into messages."""
    return (
        "\n<system-reminder>\n"
        "Current task progress:\n"
        + "\n".join(_format_lines(state))
        + "\n\nUpdate the task list as you make progress. "
        "Mark items in_progress when starting, completed when done.\n"
        "</system-reminder>"
    )


def _summarize(todos: list[TodoItem]) -> str:
    completed = sum(1 for t in todos if t.status == "completed")
    total = len(todos)
    return f"{completed}/{total} completed"


class TodoWriteTool(Tool[TodoConfig]):
    name: str = "todo_write"

    def __init__(
        self,
        config: TodoConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter | None = None,
    ) -> None:
        super().__init__(config, event, tool_progress_reporter)
        self._memory_manager: PersistentShortMemoryManager[TodoState] = (
            PersistentShortMemoryManager(
                short_term_memory_service=ShortTermMemoryService(event=event),
                short_term_memory_schema=TodoState,
                short_term_memory_name=config.memory_key,
            )
        )

    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name="todo_write",
            description=(
                "Create or update a task list to track progress on multi-step work. "
                "Use for tasks with 3+ steps. Mark items in_progress when starting, "
                "completed when done. Only one item should be in_progress at a time."
            ),
            parameters=TodoWriteInput.model_json_schema(),
        )

    def tool_description_for_system_prompt(self) -> str:
        return _TODO_SYSTEM_PROMPT

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        input_data = TodoWriteInput.model_validate(tool_call.arguments)

        current_state = await self._memory_manager.load_async() or TodoState()

        if input_data.merge:
            current_state = current_state.merge(input_data.todos)
        else:
            current_state = TodoState(
                todos=input_data.todos,
                last_updated_iteration=current_state.last_updated_iteration,
            )

        current_state.todos = current_state.todos[: self.config.max_todos]
        current_state.last_updated_iteration += 1

        await self._memory_manager.save_async(current_state)

        logger.info(
            "TodoWriteTool: saved %d items (merge=%s)",
            len(current_state.todos),
            input_data.merge,
        )

        return ToolCallResponse(
            id=tool_call.id,
            name=self.name,
            content=format_todo_state(current_state),
        )

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    def get_evaluation_checks_based_on_tool_response(
        self, tool_response: ToolCallResponse
    ) -> list[EvaluationMetricName]:
        return []


class TodoReadTool(Tool[TodoConfig]):
    name: str = "todo_read"

    def __init__(
        self,
        config: TodoConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter | None = None,
    ) -> None:
        super().__init__(config, event, tool_progress_reporter)
        self._memory_manager: PersistentShortMemoryManager[TodoState] = (
            PersistentShortMemoryManager(
                short_term_memory_service=ShortTermMemoryService(event=event),
                short_term_memory_schema=TodoState,
                short_term_memory_name=config.memory_key,
            )
        )

    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name="todo_read",
            description="Read the current task list to check progress.",
            parameters={"type": "object", "properties": {}},
        )

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        state = await self._memory_manager.load_async() or TodoState()
        return ToolCallResponse(
            id=tool_call.id,
            name=self.name,
            content=format_todo_state(state),
        )

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    def get_evaluation_checks_based_on_tool_response(
        self, tool_response: ToolCallResponse
    ) -> list[EvaluationMetricName]:
        return []
