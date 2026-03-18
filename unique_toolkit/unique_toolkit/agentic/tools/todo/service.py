from __future__ import annotations

import textwrap
from logging import getLogger

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.short_term_memory_manager.persistent_short_term_memory_manager import (
    PersistentShortMemoryManager,
)
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.todo.config import TodoConfig
from unique_toolkit.agentic.tools.todo.schemas import (
    TodoList,
    TodoStatus,
    TodoWriteInput,
)
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.language_model import LanguageModelToolDescription
from unique_toolkit.language_model.schemas import LanguageModelFunction
from unique_toolkit.short_term_memory.service import ShortTermMemoryService

logger = getLogger(__name__)

_TODO_SYSTEM_PROMPT = textwrap.dedent("""\
    You have access to a task tracking tool (todo_write). \
    Use it proactively for complex tasks with 3+ distinct steps.

    When to use:
    - Multi-step analysis or research tasks
    - Tasks requiring data from multiple sources
    - Any task where tracking progress helps avoid repeating work

    When NOT to use:
    - Simple single-step questions
    - Quick lookups or formatting tasks

    Two-phase workflow:
    1. CLARIFICATION PHASE (before creating the task list):
       Ask ALL clarifying questions in a single message. \
    Gather every piece of information you need upfront.
    2. EXECUTION PHASE (after creating the task list):
       Execute every step autonomously without stopping. \
    Do NOT ask follow-up questions. Use sensible defaults for \
    any ambiguous detail — note the assumption and move on.

    Execution rules:
    - After creating a task list, execute each step IMMEDIATELY. \
    Do NOT ask the user for confirmation between steps.
    - Work through ALL items autonomously until the list is complete.
    - Mark only ONE item as in_progress at a time.
    - Update status immediately after completing each step.
    - When a detail is unclear, choose the most reasonable default \
    rather than stopping to ask. Document your assumption in the \
    todo item or response.
    - The ONLY reason to stop mid-execution is a hard blocker: \
    missing credentials, a required resource that does not exist, \
    or an unrecoverable error.""")

_TODO_EXECUTION_REMINDER = (
    "You are in the EXECUTION PHASE. "
    "Do NOT ask the user any questions or request confirmation. "
    "Pick the next pending item, mark it in_progress, execute it, "
    "mark it completed, and continue to the next item. "
    "If anything is ambiguous, choose a sensible default and note the assumption."
)


class TodoWriteTool(Tool[TodoConfig]):
    name: str = "todo_write"

    def __init__(
        self,
        config: TodoConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter | None = None,
    ) -> None:
        super().__init__(config, event, tool_progress_reporter)
        self._memory_manager: PersistentShortMemoryManager[TodoList] = (
            PersistentShortMemoryManager(
                short_term_memory_service=ShortTermMemoryService(event=event),
                short_term_memory_schema=TodoList,
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

        logger.debug(
            "TodoWriteTool input: merge=%s, items=%s",
            input_data.merge,
            [
                {"id": t.id, "content": t.content, "status": t.status}
                for t in input_data.todos
            ],
        )

        current_state = await self._memory_manager.load_async() or TodoList()

        if input_data.merge:
            current_state = current_state.update(input_data.todos)
        else:
            current_state = TodoList(
                todos=input_data.todos,
                last_updated_iteration=current_state.last_updated_iteration,
            )

        current_state.todos = current_state.todos[: self.config.max_todos]
        current_state.last_updated_iteration += 1

        try:
            await self._memory_manager.save_async(current_state)
        except Exception:
            logger.warning(
                "TodoWriteTool: failed to persist state, continuing with in-memory state",
                exc_info=True,
            )

        logger.info(
            "TodoWriteTool: saved %d items (merge=%s) — %s",
            len(current_state.todos),
            input_data.merge,
            current_state.format(),
        )

        return ToolCallResponse(
            id=tool_call.id,
            name=self.name,
            content=current_state.format(),
            system_reminder=_TODO_EXECUTION_REMINDER
            if current_state.has_active_items()
            else "",
            debug_info={
                "input": {
                    "merge": input_data.merge,
                    "items": [t.model_dump() for t in input_data.todos],
                },
                "state": {
                    "total": len(current_state.todos),
                    "completed": sum(
                        1
                        for t in current_state.todos
                        if t.status == TodoStatus.COMPLETED
                    ),
                    "in_progress": sum(
                        1
                        for t in current_state.todos
                        if t.status == TodoStatus.IN_PROGRESS
                    ),
                    "pending": sum(
                        1 for t in current_state.todos if t.status == TodoStatus.PENDING
                    ),
                    "items": [t.model_dump() for t in current_state.todos],
                },
                "iteration": current_state.last_updated_iteration,
            },
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
        self._memory_manager: PersistentShortMemoryManager[TodoList] = (
            PersistentShortMemoryManager(
                short_term_memory_service=ShortTermMemoryService(event=event),
                short_term_memory_schema=TodoList,
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
        try:
            state = await self._memory_manager.load_async() or TodoList()
        except Exception:
            logger.warning(
                "TodoReadTool: failed to load state, returning empty state",
                exc_info=True,
            )
            state = TodoList()
        return ToolCallResponse(
            id=tool_call.id,
            name=self.name,
            content=state.format(),
        )

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    def get_evaluation_checks_based_on_tool_response(
        self, tool_response: ToolCallResponse
    ) -> list[EvaluationMetricName]:
        return []
