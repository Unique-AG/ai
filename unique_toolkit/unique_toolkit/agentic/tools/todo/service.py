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
    TodoList,
    TodoWriteInput,
)
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.language_model import LanguageModelToolDescription
from unique_toolkit.language_model.schemas import LanguageModelFunction
from unique_toolkit.short_term_memory.service import ShortTermMemoryService

logger = getLogger(__name__)

_DEFAULT_SYSTEM_PROMPT = """\
You have access to a task tracking tool (todo_write). Use it liberally — any task involving multiple tool calls should use todo_write to track progress. The user sees the task list as a live progress indicator, so using it is helpful even for moderately complex tasks.

When to use:
- Any task that will require 2 or more tool calls
- Multi-step workflows (research, analysis, document processing, comparisons)
- Batch operations: when asked to process ALL items matching a criteria (e.g. all emails, all documents, all entries), create a todo for each item so none are skipped
- Any task where tracking progress prevents repeating or forgetting work

When NOT to use:
- Simple single-step questions or quick lookups that need at most one tool call

Two-phase workflow:
1. CLARIFICATION PHASE (before creating the task list): Ask ALL clarifying questions in a single message. Gather every piece of information you need upfront.
2. EXECUTION PHASE (after creating the task list): Execute every step autonomously without stopping. Do NOT ask follow-up questions. Use sensible defaults for any ambiguous detail — note the assumption and move on.

Execution rules:
- After creating a task list, execute each step IMMEDIATELY. Do NOT ask the user for confirmation between steps.
- Work through ALL items autonomously until every item is in a terminal state (completed or cancelled).
- When working on multiple items in parallel, mark ALL of them as in_progress — do not limit yourself to one at a time.
- Combine todo_write with work tool calls in the same response. For example, call todo_write (to update statuses) alongside your WebSearch or other tool calls — do not waste a separate turn on bookkeeping alone.
- When a detail is unclear, choose the most reasonable default rather than stopping to ask. Document your assumption.
- Do NOT summarize remaining items or ask if you should continue. Just keep going.
- The ONLY reason to stop mid-execution is a hard blocker: missing credentials, a required resource that does not exist, or an unrecoverable error.

Completion rules:
- Before writing your final response, you MUST call todo_write one last time to mark every remaining item as completed or cancelled. Your final todo list must have ZERO pending or in_progress items.
- Never write a final response while items are still pending. If items remain, keep executing them.
- For complex tasks, include a final "verify and synthesize" item in your todo list to ensure a clean wrap-up.

Iteration budget:
- You have a limited number of iterations. On the final iteration, all tools (including todo_write) are removed. You MUST mark all items completed/cancelled BEFORE that final iteration.
- Items that require only analysis or synthesis (no external tool) should be marked completed as soon as you have the data, even if you write the analysis in a later response."""

_DEFAULT_EXECUTION_REMINDER = "You are in the EXECUTION PHASE. Do NOT ask the user any questions or request confirmation. You MUST process every pending item — do not skip or summarize. Always include a todo_write call alongside your work tool calls in the same response — mark items in_progress before executing and completed after. Do not use a separate turn just for status updates. Do NOT write a final text response while items are still pending or in_progress — keep executing until every item reaches a terminal state (completed/cancelled), then call todo_write one final time before responding."


def _chat_scoped_stm_service(event: ChatEvent) -> ShortTermMemoryService:
    """Build an STM service scoped to chat only (no messageId).

    The backend rejects create requests when all three of chatId, messageId,
    and companyId are present (companyId is always injected from auth).
    Todo state is chat-scoped anyway, so omitting messageId is correct.
    """
    return ShortTermMemoryService(
        company_id=event.company_id,
        user_id=event.user_id,
        chat_id=event.payload.chat_id,
        message_id=None,
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
                short_term_memory_service=_chat_scoped_stm_service(event),
                short_term_memory_schema=TodoList,
                short_term_memory_name=config.memory_key,
            )
        )
        self._cached_state: TodoList | None = None

    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name="todo_write",
            description=(
                "Create or update a task list to track progress. "
                "Use for any task involving multiple tool calls — the user sees "
                "this as a live progress indicator. Mark items in_progress when "
                "starting, completed when done. You can mark multiple items "
                "in_progress if working on them in parallel."
            ),
            parameters=TodoWriteInput.model_json_schema(),
        )

    def tool_description_for_system_prompt(self) -> str:
        return self.config.system_prompt or _DEFAULT_SYSTEM_PROMPT

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        try:
            input_data = TodoWriteInput.model_validate(tool_call.arguments)
        except Exception as e:
            logger.warning("TodoWriteTool: input validation failed: %s", e)
            return ToolCallResponse(
                id=tool_call.id,
                name=self.name,
                content=f"Error: invalid input — {e}. "
                "When using merge=True, each item needs at least 'id' and 'status'. "
                "When using merge=False (new list), each item also needs 'content'.",
            )

        logger.debug(
            "TodoWriteTool input: merge=%s, items=%s",
            input_data.merge,
            [
                {"id": t.id, "content": t.content, "status": t.status}
                for t in input_data.todos
            ],
        )

        current_state = await self._load_state()

        if input_data.merge:
            current_state = current_state.update(input_data.todos)
        else:
            current_state = TodoList(
                todos=[
                    TodoItem(id=t.id, content=t.content or "", status=t.status)
                    for t in input_data.todos
                ],
                last_updated_iteration=current_state.last_updated_iteration,
            )

        current_state.last_updated_iteration += 1
        self._cached_state = current_state

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

        reminder = self.config.execution_reminder or _DEFAULT_EXECUTION_REMINDER

        counts = current_state.status_counts()

        return ToolCallResponse(
            id=tool_call.id,
            name=self.name,
            content=current_state.format(),
            system_reminder=reminder if current_state.has_active_items() else "",
            debug_info={
                "input": {
                    "merge": input_data.merge,
                    "items": [t.model_dump() for t in input_data.todos],
                },
                "state": {
                    **counts,
                    "items": [t.model_dump() for t in current_state.todos],
                },
                "iteration": current_state.last_updated_iteration,
            },
        )

    async def _load_state(self) -> TodoList:
        """Load state from persistence, falling back to in-memory cache."""
        try:
            persisted = await self._memory_manager.load_async()
            if persisted is not None:
                self._cached_state = persisted
                return persisted
        except Exception:
            logger.warning(
                "TodoWriteTool: failed to load persisted state",
                exc_info=True,
            )

        if self._cached_state is not None:
            logger.debug("TodoWriteTool: using in-memory cached state")
            return self._cached_state

        return TodoList()

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    def get_evaluation_checks_based_on_tool_response(
        self, tool_response: ToolCallResponse
    ) -> list[EvaluationMetricName]:
        return []
