from __future__ import annotations

from collections import Counter
from logging import getLogger

from unique_toolkit._common.utils.jinja.render import render_template
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.short_term_memory_manager.persistent_short_term_memory_manager import (
    PersistentShortMemoryManager,
)
from unique_toolkit.agentic.tools.experimental.todo.config import TodoConfig
from unique_toolkit.agentic.tools.experimental.todo.schemas import (
    TodoItem,
    TodoList,
    TodoStatus,
    TodoWriteInput,
)
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.schemas import MessageLog, MessageLogStatus
from unique_toolkit.language_model import LanguageModelToolDescription
from unique_toolkit.language_model.schemas import LanguageModelFunction
from unique_toolkit.short_term_memory.service import ShortTermMemoryService

logger = getLogger(__name__)


MEMORY_KEY = "agent_todo_state"

_STATUS_ICON = {
    TodoStatus.COMPLETED: "✓",
    TodoStatus.IN_PROGRESS: "→",
    TodoStatus.CANCELLED: "✗",
    TodoStatus.PENDING: "○",
}


class TodoWriteTool(Tool[TodoConfig]):
    name: str = "TodoWrite"

    def __init__(
        self,
        config: TodoConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter | None = None,
    ) -> None:
        super().__init__(config, event, tool_progress_reporter)
        stm_service = ShortTermMemoryService(
            company_id=event.company_id,
            user_id=event.user_id,
            chat_id=event.payload.chat_id,
            message_id=None,
        )
        self._memory_manager: PersistentShortMemoryManager[TodoList] = (
            PersistentShortMemoryManager(
                short_term_memory_service=stm_service,
                short_term_memory_schema=TodoList,
                short_term_memory_name=MEMORY_KEY,
            )
        )
        self._cached_state: TodoList | None = None
        self._plan_log: MessageLog | None = None

    def display_name(self) -> str:
        return self.config.display_name

    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name=self.name,
            description=render_template(
                self.config.tool_description,
                parallel_mode=self.config.parallel_mode,
            ),
            parameters=TodoWriteInput.model_json_schema(),
        )

    def tool_description_for_system_prompt(self) -> str:
        return render_template(
            self.config.system_prompt,
            parallel_mode=self.config.parallel_mode,
        )

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
                    TodoItem(
                        id=t.id,
                        content=t.content or "",
                        status=t.status,
                        active_form=t.active_form,
                    )
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

        counts = current_state.status_counter()
        await self._log_step(current_state)

        content = current_state.format()
        content = self._maybe_add_verification_nudge(content, counts)

        return ToolCallResponse(
            id=tool_call.id,
            name=self.name,
            content=content,
            system_reminder=render_template(
                self.config.execution_reminder,
                parallel_mode=self.config.parallel_mode,
            )
            if current_state.has_active_items()
            else "",
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

    async def _log_step(self, state: TodoList) -> None:
        """Write a single Steps panel entry summarising the current todo state.

        Shows a numbered list of all items with status indicators (✓/→/○)
        and a completion count header. In-progress items display their
        ``active_form`` (present-continuous description) when available.
        """
        try:
            counts = state.status_counter()
            completed = counts["completed"]
            total = len(state.todos)

            if total == 0:
                return

            all_done = not counts["in_progress"] and not counts["pending"]

            lines = []
            for i, t in enumerate(state.todos, 1):
                icon = _STATUS_ICON.get(t.status, "○")
                if t.status == TodoStatus.IN_PROGRESS:
                    label = t.active_form or t.content
                else:
                    label = t.content
                lines.append(f"{icon} {i}. {label}")
            plan_text = "\n".join(lines)

            self._plan_log = (
                await self._message_step_logger.create_or_update_message_log_async(
                    active_message_log=self._plan_log,
                    header=self.display_name(),
                    progress_message=f"{completed}/{total} completed\n{plan_text}",
                    status=(
                        MessageLogStatus.COMPLETED
                        if all_done
                        else MessageLogStatus.RUNNING
                    ),
                )
            )
        except Exception:
            logger.debug("TodoWriteTool: failed to write step log", exc_info=True)

    def _maybe_add_verification_nudge(self, content: str, counts: Counter[str]) -> str:
        """Append a verification nudge after N consecutive completions."""
        threshold = self.config.verification_threshold
        if threshold <= 0:
            return content
        completed = counts["completed"]
        if completed > 0 and completed % threshold == 0 and counts["pending"]:
            nudge = render_template(self.config.verification_nudge, completed=completed)
            content += f"\n\n{nudge}"
        return content

    async def _load_state(self) -> TodoList:
        """Load state from persistence, falling back to in-memory cache.

        When both persisted and cached state exist, prefer whichever has the
        higher ``last_updated_iteration`` — the cache may be ahead if a
        previous ``save_async`` failed.
        """
        persisted: TodoList | None = None
        try:
            persisted = await self._memory_manager.load_async()
        except Exception:
            logger.warning(
                "TodoWriteTool: failed to load persisted state",
                exc_info=True,
            )

        if persisted is not None and self._cached_state is not None:
            if (
                self._cached_state.last_updated_iteration
                > persisted.last_updated_iteration
            ):
                logger.info(
                    "TodoWriteTool: cache (iter %d) is ahead of persisted (iter %d), keeping cache",
                    self._cached_state.last_updated_iteration,
                    persisted.last_updated_iteration,
                )
                return self._cached_state
            self._cached_state = persisted
            return persisted

        if persisted is not None:
            self._cached_state = persisted
            return persisted

        if self._cached_state is not None:
            logger.debug("TodoWriteTool: using in-memory cached state")
            return self._cached_state

        return TodoList(todos=[], last_updated_iteration=0)

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    def get_evaluation_checks_based_on_tool_response(
        self, tool_response: ToolCallResponse
    ) -> list[EvaluationMetricName]:
        return []
