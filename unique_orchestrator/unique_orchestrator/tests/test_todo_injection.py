from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, Field
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
)

try:
    from unique_toolkit.agentic.tools.todo.schemas import TodoItem, TodoList

    HAS_TODO_MODULE = True
except ImportError:
    HAS_TODO_MODULE = False

    TodoStatus = Literal["pending", "in_progress", "completed", "cancelled"]

    class TodoItem(BaseModel):  # type: ignore[no-redef]
        id: str
        content: str
        status: TodoStatus

    class TodoList(BaseModel):  # type: ignore[no-redef]
        todos: list[TodoItem] = Field(default_factory=list)
        last_updated_iteration: int = 0

        def has_active_items(self) -> bool:
            return any(t.status not in ("completed", "cancelled") for t in self.todos)

        def format_reminder(self) -> str:
            lines = [
                f"  [{'x' if t.status == 'completed' else '>' if t.status == 'in_progress' else '-' if t.status == 'cancelled' else ' '}] {t.content} (id: {t.id})"
                for t in self.todos
            ]
            return (
                "\n<system-reminder>\n"
                "Current task progress:\n"
                + "\n".join(lines)
                + "\n\nUpdate the task list as you make progress. "
                "Mark items in_progress when starting, completed when done.\n"
                "</system-reminder>"
            )


requires_todo = pytest.mark.skipif(
    not HAS_TODO_MODULE,
    reason="unique_toolkit.agentic.tools.todo not installed (needs toolkit >= 1.53.0)",
)

if TYPE_CHECKING:
    from unique_orchestrator.unique_ai import UniqueAI


def _make_messages(*user_texts: str) -> LanguageModelMessages:
    """Build a minimal LanguageModelMessages with a system + user messages."""
    msgs: list = [LanguageModelSystemMessage(content="System prompt.")]
    for text in user_texts:
        msgs.append(LanguageModelUserMessage(content=text))
    return LanguageModelMessages(root=msgs)


def _build_unique_ai(
    todo_memory_manager=None,
) -> "UniqueAI":
    from unique_orchestrator.unique_ai import UniqueAI

    dummy_event = MagicMock()
    dummy_event.payload.assistant_message.id = "assist_1"
    dummy_event.payload.user_message.text = "query"
    dummy_event.payload.user_metadata = None
    dummy_event.payload.mcp_servers = []

    mock_config = MagicMock()
    mock_config.agent.prompt_config.user_metadata = []
    mock_config.agent.prompt_config.user_message_prompt_template = "{{ query }}"
    mock_config.agent.prompt_config.system_prompt_template = "System."
    mock_config.agent.experimental.sub_agents_config.referencing_config = None
    mock_config.agent.experimental.loop_configuration.max_tool_calls_per_iteration = 5
    mock_config.agent.experimental.temperature = 0.0
    mock_config.agent.experimental.additional_llm_options = {}
    mock_config.effective_max_loop_iterations = 5
    mock_config.space.language_model.model_dump.return_value = {}
    mock_config.space.project_name = "TestProject"
    mock_config.space.custom_instructions = ""
    mock_config.space.user_space_instructions = None

    mock_tool_manager = MagicMock()
    mock_tool_manager.get_tool_prompts.return_value = []
    mock_tool_manager.filter_tool_calls.return_value = []

    mock_history_manager = MagicMock()
    mock_history_manager.get_tool_calls.return_value = []

    mock_content_service = MagicMock()
    mock_content_service.get_documents_uploaded_to_chat.return_value = []

    ua = UniqueAI(
        logger=MagicMock(),
        event=dummy_event,
        config=mock_config,
        chat_service=MagicMock(),
        content_service=mock_content_service,
        debug_info_manager=MagicMock(),
        streaming_handler=MagicMock(),
        reference_manager=MagicMock(),
        thinking_manager=MagicMock(),
        tool_manager=mock_tool_manager,
        history_manager=mock_history_manager,
        evaluation_manager=MagicMock(),
        postprocessor_manager=MagicMock(),
        message_step_logger=MagicMock(),
        mcp_servers=[],
        loop_iteration_runner=MagicMock(),
        todo_memory_manager=todo_memory_manager,
    )
    return ua


class TestTodoInjection:
    """Test suite for TODO system-reminder injection in UniqueAI._compose_message_plan_execution"""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_compose_messages__todo_disabled__no_reminder(self) -> None:
        """
        Purpose: Verify no injection when todo_memory_manager is None.
        Why: Default behavior -- existing spaces have no TODO tools.
        Setup: Build UniqueAI without todo_memory_manager.
        """
        ua = _build_unique_ai(todo_memory_manager=None)

        messages = _make_messages("Hello")
        ua._history_manager.get_history_for_model_call = AsyncMock(
            return_value=messages
        )

        result = await ua._compose_message_plan_execution()

        last_user = [m for m in result.root if m.role.value == "user"][-1]
        assert "<system-reminder>" not in last_user.content

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_compose_messages__todo_enabled_no_state__no_reminder(self) -> None:
        """
        Purpose: Verify no injection when TODO state is empty (no todos created yet).
        Why: First iteration before model calls todo_write.
        Setup: Mock memory manager returns None.
        """
        mock_mm = MagicMock()
        mock_mm.load_async = AsyncMock(return_value=None)
        ua = _build_unique_ai(todo_memory_manager=mock_mm)

        messages = _make_messages("Hello")
        ua._history_manager.get_history_for_model_call = AsyncMock(
            return_value=messages
        )

        result = await ua._compose_message_plan_execution()

        last_user = [m for m in result.root if m.role.value == "user"][-1]
        assert "<system-reminder>" not in last_user.content

    @requires_todo
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_compose_messages__todo_enabled_with_state__injects_reminder(
        self,
    ) -> None:
        """
        Purpose: Verify injection when there are active TODO items.
        Why: Core feature -- the model needs to see current task progress.
        Setup: Mock memory manager returns state with pending items.
        """
        state = TodoList(
            todos=[
                TodoItem(id="t1", content="Research APIs", status="completed"),
                TodoItem(id="t2", content="Build service", status="in_progress"),
                TodoItem(id="t3", content="Write tests", status="pending"),
            ]
        )
        mock_mm = MagicMock()
        mock_mm.load_async = AsyncMock(return_value=state)
        ua = _build_unique_ai(todo_memory_manager=mock_mm)

        messages = _make_messages("Continue working")
        ua._history_manager.get_history_for_model_call = AsyncMock(
            return_value=messages
        )

        result = await ua._compose_message_plan_execution()

        last_user = [m for m in result.root if m.role.value == "user"][-1]
        assert "<system-reminder>" in last_user.content
        assert "Research APIs" in last_user.content
        assert "Build service" in last_user.content
        assert "Write tests" in last_user.content

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_compose_messages__all_completed__no_reminder(self) -> None:
        """
        Purpose: Verify no injection when all items are completed.
        Why: No active tasks means no progress reminder needed.
        Setup: Mock memory manager returns state with only completed items.
        """
        state = TodoList(
            todos=[
                TodoItem(id="t1", content="Done task", status="completed"),
                TodoItem(id="t2", content="Also done", status="completed"),
            ]
        )
        mock_mm = MagicMock()
        mock_mm.load_async = AsyncMock(return_value=state)
        ua = _build_unique_ai(todo_memory_manager=mock_mm)

        messages = _make_messages("All done?")
        ua._history_manager.get_history_for_model_call = AsyncMock(
            return_value=messages
        )

        result = await ua._compose_message_plan_execution()

        last_user = [m for m in result.root if m.role.value == "user"][-1]
        assert "<system-reminder>" not in last_user.content

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_compose_messages__completed_and_cancelled__no_reminder(
        self,
    ) -> None:
        """
        Purpose: Verify no injection when all items are completed or cancelled.
        Why: Cancelled tasks are not actionable; only pending/in_progress are.
        Setup: Mix of completed and cancelled items, no pending or in_progress.
        """
        state = TodoList(
            todos=[
                TodoItem(id="t1", content="Done task", status="completed"),
                TodoItem(id="t2", content="Dropped task", status="cancelled"),
            ]
        )
        mock_mm = MagicMock()
        mock_mm.load_async = AsyncMock(return_value=state)
        ua = _build_unique_ai(todo_memory_manager=mock_mm)

        messages = _make_messages("What's left?")
        ua._history_manager.get_history_for_model_call = AsyncMock(
            return_value=messages
        )

        result = await ua._compose_message_plan_execution()

        last_user = [m for m in result.root if m.role.value == "user"][-1]
        assert "<system-reminder>" not in last_user.content

    @requires_todo
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_reminder__appended_to_last_user_message(self) -> None:
        """
        Purpose: Verify the reminder is appended to the LAST user message.
        Why: Earlier user messages should not be modified; prompt caching depends on this.
        Setup: Two user messages, verify only the last one has the reminder.
        """
        state = TodoList(todos=[TodoItem(id="t1", content="Task A", status="pending")])
        mock_mm = MagicMock()
        mock_mm.load_async = AsyncMock(return_value=state)
        ua = _build_unique_ai(todo_memory_manager=mock_mm)

        messages = _make_messages("First question", "Second question")
        ua._history_manager.get_history_for_model_call = AsyncMock(
            return_value=messages
        )

        result = await ua._compose_message_plan_execution()

        user_msgs = [m for m in result.root if m.role.value == "user"]
        assert "<system-reminder>" not in user_msgs[0].content
        assert "<system-reminder>" in user_msgs[1].content

    @requires_todo
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_reminder_format__contains_status_icons(self) -> None:
        """
        Purpose: Verify the reminder uses correct status icons.
        Why: Visual clarity for the model to parse task states.
        Setup: State with one item of each status type.
        """
        state = TodoList(
            todos=[
                TodoItem(id="a", content="Pending one", status="pending"),
                TodoItem(id="b", content="Active one", status="in_progress"),
                TodoItem(id="c", content="Done one", status="completed"),
                TodoItem(id="d", content="Dropped one", status="cancelled"),
            ]
        )
        mock_mm = MagicMock()
        mock_mm.load_async = AsyncMock(return_value=state)
        ua = _build_unique_ai(todo_memory_manager=mock_mm)

        messages = _make_messages("Check progress")
        ua._history_manager.get_history_for_model_call = AsyncMock(
            return_value=messages
        )

        result = await ua._compose_message_plan_execution()

        last_user = [m for m in result.root if m.role.value == "user"][-1]
        assert "[ ] Pending one" in last_user.content
        assert "[>] Active one" in last_user.content
        assert "[x] Done one" in last_user.content
        assert "[-] Dropped one" in last_user.content

    @requires_todo
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_reminder__preserves_original_user_message(self) -> None:
        """
        Purpose: Verify the original user text is preserved (not replaced).
        Why: The reminder is appended, not substituted.
        Setup: User message with specific text, verify it still starts with that text.
        """
        state = TodoList(todos=[TodoItem(id="t1", content="Task A", status="pending")])
        mock_mm = MagicMock()
        mock_mm.load_async = AsyncMock(return_value=state)
        ua = _build_unique_ai(todo_memory_manager=mock_mm)

        messages = _make_messages("Please analyze the report")
        ua._history_manager.get_history_for_model_call = AsyncMock(
            return_value=messages
        )

        result = await ua._compose_message_plan_execution()

        last_user = [m for m in result.root if m.role.value == "user"][-1]
        assert last_user.content.startswith("Please analyze the report")
        assert "<system-reminder>" in last_user.content


class TestBuildTodoMemoryManager:
    """Tests for _build_todo_memory_manager in the builder."""

    @pytest.mark.ai
    def test_returns_none_when_todo_tracking_disabled(self) -> None:
        """
        Purpose: Verify no memory manager when todo_tracking is None.
        Why: Default config has no todo tracking.
        Setup: Config with todo_tracking=None in experimental.
        """
        from unique_orchestrator.unique_ai_builder import _build_todo_memory_manager

        mock_event = MagicMock()
        mock_config = MagicMock()
        mock_config.agent.experimental.todo_tracking = None

        result = _build_todo_memory_manager(mock_event, mock_config)

        assert result is None

    @requires_todo
    @pytest.mark.ai
    def test_returns_manager_when_todo_tracking_enabled(self) -> None:
        """
        Purpose: Verify memory manager is created when todo_tracking is configured.
        Why: Enables system-reminder injection.
        Setup: Config with todo_tracking set to defaults.
        """
        from unique_orchestrator.config import TodoTrackingConfig
        from unique_orchestrator.unique_ai_builder import _build_todo_memory_manager

        mock_event = MagicMock()
        mock_config = MagicMock()
        mock_config.agent.experimental.todo_tracking = TodoTrackingConfig()

        result = _build_todo_memory_manager(mock_event, mock_config)

        assert result is not None

    @requires_todo
    @pytest.mark.ai
    def test_returns_none_when_inject_system_reminder_is_false(self) -> None:
        """
        Purpose: Verify no memory manager when config disables injection.
        Why: inject_system_reminder=False allows using the tool without injection.
        Setup: Config with todo_tracking enabled but inject_system_reminder=False.
        """
        from unique_orchestrator.config import TodoTrackingConfig
        from unique_orchestrator.unique_ai_builder import _build_todo_memory_manager

        mock_event = MagicMock()
        mock_config = MagicMock()
        mock_config.agent.experimental.todo_tracking = TodoTrackingConfig(
            inject_system_reminder=False
        )

        result = _build_todo_memory_manager(mock_event, mock_config)

        assert result is None
