"""Tests for TodoWriteTool, TodoList, and related schemas.

Covers:
- TodoList.update() logic (update, append, preserve, active_form carry-over)
- TodoList.has_active_items() logic
- TodoList.status_counts() aggregation
- TodoWriteTool.run() (create, update, replace, formatting)
- Large todo lists (100 items) preserved without truncation
- debug_info structure on tool response
- system_reminder set when active items, empty when all terminal
- _log_step() Steps panel integration (counts and active_form display)
- Verification nudge after N completions
- parallel_mode config toggling descriptions and reminders
- Tool registration, config validation
- Configurable prompts via TodoConfig
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_toolkit.agentic.tools.experimental.todo.config import (
    _DEFAULT_SYSTEM_PROMPT,
    _DEFAULT_TOOL_DESCRIPTION,
    _PARALLEL_EXECUTION_REMINDER,
    _PARALLEL_EXECUTION_RULES,
    _PARALLEL_TOOL_DESCRIPTION,
    TodoConfig,
)
from unique_toolkit.agentic.tools.experimental.todo.schemas import (
    TodoItem,
    TodoItemInput,
    TodoList,
    TodoStatus,
    TodoWriteInput,
)
from unique_toolkit.agentic.tools.experimental.todo.service import (
    TodoWriteTool,
)
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.chat.schemas import MessageLogStatus


@pytest.fixture(autouse=True)
def ensure_todo_tool_registered():
    """Ensure TodoWriteTool is registered in ToolFactory before tests run.

    Other test modules may clear the ToolFactory state, which removes the
    registration that happened at module import time.
    """
    if "todo_write" not in ToolFactory.tool_config_map:
        ToolFactory.register_tool(TodoWriteTool, TodoConfig)
    yield


class TestTodoList:
    def test_empty_format(self) -> None:
        tl = TodoList()
        assert tl.format() == "No tasks tracked."

    def test_format_with_items(self) -> None:
        tl = TodoList(
            todos=[
                TodoItem(id="a", content="Task A", status=TodoStatus.PENDING),
                TodoItem(id="b", content="Task B", status=TodoStatus.COMPLETED),
            ]
        )
        formatted = tl.format()
        assert "0/2 completed" not in formatted or "1/2 completed" in formatted
        assert "[ ] Task A" in formatted
        assert "[x] Task B" in formatted

    def test_has_active_items_with_pending(self) -> None:
        tl = TodoList(todos=[TodoItem(id="a", content="x", status=TodoStatus.PENDING)])
        assert tl.has_active_items() is True

    def test_has_active_items_with_in_progress(self) -> None:
        tl = TodoList(
            todos=[TodoItem(id="a", content="x", status=TodoStatus.IN_PROGRESS)]
        )
        assert tl.has_active_items() is True

    def test_has_active_items_all_completed(self) -> None:
        tl = TodoList(
            todos=[TodoItem(id="a", content="x", status=TodoStatus.COMPLETED)]
        )
        assert tl.has_active_items() is False

    def test_has_active_items_all_cancelled(self) -> None:
        tl = TodoList(
            todos=[TodoItem(id="a", content="x", status=TodoStatus.CANCELLED)]
        )
        assert tl.has_active_items() is False

    def test_has_active_items_empty(self) -> None:
        tl = TodoList()
        assert tl.has_active_items() is False

    def test_status_counts(self) -> None:
        tl = TodoList(
            todos=[
                TodoItem(id="a", content="x", status=TodoStatus.PENDING),
                TodoItem(id="b", content="x", status=TodoStatus.IN_PROGRESS),
                TodoItem(id="c", content="x", status=TodoStatus.COMPLETED),
                TodoItem(id="d", content="x", status=TodoStatus.CANCELLED),
                TodoItem(id="e", content="x", status=TodoStatus.PENDING),
            ]
        )
        counts = tl.status_counts()
        assert counts == {
            "total": 5,
            "pending": 2,
            "in_progress": 1,
            "completed": 1,
            "cancelled": 1,
        }


class TestTodoListUpdate:
    def test_update_existing_item(self) -> None:
        tl = TodoList(
            todos=[TodoItem(id="a", content="Task A", status=TodoStatus.PENDING)]
        )
        updated = tl.update([TodoItemInput(id="a", status=TodoStatus.COMPLETED)])
        assert updated.todos[0].status == TodoStatus.COMPLETED
        assert updated.todos[0].content == "Task A"

    def test_append_new_item(self) -> None:
        tl = TodoList(
            todos=[TodoItem(id="a", content="Task A", status=TodoStatus.PENDING)]
        )
        updated = tl.update(
            [TodoItemInput(id="b", content="Task B", status=TodoStatus.PENDING)]
        )
        assert len(updated.todos) == 2
        assert updated.todos[1].id == "b"

    def test_preserve_unmentioned(self) -> None:
        tl = TodoList(
            todos=[
                TodoItem(id="a", content="Task A", status=TodoStatus.PENDING),
                TodoItem(id="b", content="Task B", status=TodoStatus.PENDING),
            ]
        )
        updated = tl.update([TodoItemInput(id="a", status=TodoStatus.COMPLETED)])
        assert len(updated.todos) == 2
        assert updated.todos[0].status == TodoStatus.COMPLETED
        assert updated.todos[1].status == TodoStatus.PENDING

    def test_update_preserves_content_when_omitted(self) -> None:
        tl = TodoList(
            todos=[TodoItem(id="a", content="Original", status=TodoStatus.PENDING)]
        )
        updated = tl.update(
            [TodoItemInput(id="a", content=None, status=TodoStatus.IN_PROGRESS)]
        )
        assert updated.todos[0].content == "Original"

    def test_new_item_without_content_gets_empty_string(self) -> None:
        tl = TodoList()
        updated = tl.update(
            [TodoItemInput(id="a", content=None, status=TodoStatus.PENDING)]
        )
        assert updated.todos[0].content == ""

    def test_update_preserves_iteration_counter(self) -> None:
        tl = TodoList(last_updated_iteration=5)
        updated = tl.update(
            [TodoItemInput(id="a", content="x", status=TodoStatus.PENDING)]
        )
        assert updated.last_updated_iteration == 5

    def test_update_preserves_active_form_when_omitted(self) -> None:
        tl = TodoList(
            todos=[
                TodoItem(
                    id="a",
                    content="Task A",
                    status=TodoStatus.PENDING,
                    active_form="Doing Task A",
                )
            ]
        )
        updated = tl.update([TodoItemInput(id="a", status=TodoStatus.IN_PROGRESS)])
        assert updated.todos[0].active_form == "Doing Task A"

    def test_update_overwrites_active_form_when_supplied(self) -> None:
        tl = TodoList(
            todos=[
                TodoItem(
                    id="a",
                    content="Task A",
                    status=TodoStatus.PENDING,
                    active_form="Old form",
                )
            ]
        )
        updated = tl.update(
            [
                TodoItemInput(
                    id="a",
                    status=TodoStatus.IN_PROGRESS,
                    active_form="New form",
                )
            ]
        )
        assert updated.todos[0].active_form == "New form"

    def test_new_item_without_active_form_is_none(self) -> None:
        tl = TodoList()
        updated = tl.update(
            [TodoItemInput(id="a", content="x", status=TodoStatus.PENDING)]
        )
        assert updated.todos[0].active_form is None


class TestTodoWriteInput:
    def test_min_length_validation(self) -> None:
        with pytest.raises(Exception):
            TodoWriteInput(todos=[], merge=True)

    def test_default_merge_is_true(self) -> None:
        inp = TodoWriteInput(
            todos=[TodoItemInput(id="a", content="x", status=TodoStatus.PENDING)]
        )
        assert inp.merge is True


def _make_tool(
    config: TodoConfig | None = None,
) -> TodoWriteTool:
    """Create a TodoWriteTool with mocked dependencies."""
    config = config or TodoConfig()
    event = MagicMock()
    event.company_id = "test-company"
    event.user_id = "test-user"
    event.payload.chat_id = "test-chat"

    tool = TodoWriteTool(config=config, event=event)
    tool._memory_manager = MagicMock()
    tool._memory_manager.load_async = AsyncMock(return_value=None)
    tool._memory_manager.save_async = AsyncMock()
    tool._message_step_logger = MagicMock()
    tool._message_step_logger.create_or_update_message_log_async = AsyncMock()
    return tool


def _make_tool_call(arguments: dict, call_id: str = "call-1") -> MagicMock:
    tc = MagicMock()
    tc.id = call_id
    tc.arguments = arguments
    return tc


class TestTodoWriteTool:
    @pytest.mark.asyncio
    async def test_create_new_list(self) -> None:
        tool = _make_tool()
        tc = _make_tool_call(
            {
                "todos": [
                    {"id": "t1", "content": "Research APIs", "status": "pending"},
                    {"id": "t2", "content": "Write code", "status": "pending"},
                ],
                "merge": False,
            }
        )

        response = await tool.run(tc)

        assert response.name == "todo_write"
        assert "Research APIs" in response.content
        assert "Write code" in response.content
        assert "0/2 completed" in response.content
        assert response.system_reminder != ""

    @pytest.mark.asyncio
    async def test_merge_updates_existing(self) -> None:
        tool = _make_tool()
        tool._cached_state = TodoList(
            todos=[
                TodoItem(id="t1", content="Research APIs", status=TodoStatus.PENDING),
            ]
        )
        tool._memory_manager.load_async = AsyncMock(return_value=None)

        tc = _make_tool_call(
            {
                "todos": [{"id": "t1", "status": "completed"}],
                "merge": True,
            }
        )

        response = await tool.run(tc)

        assert "[x] Research APIs" in response.content

    @pytest.mark.asyncio
    async def test_system_reminder_empty_when_all_terminal(self) -> None:
        tool = _make_tool()
        tc = _make_tool_call(
            {
                "todos": [
                    {"id": "t1", "content": "Done", "status": "completed"},
                    {"id": "t2", "content": "Skipped", "status": "cancelled"},
                ],
                "merge": False,
            }
        )

        response = await tool.run(tc)

        assert response.system_reminder == ""

    @pytest.mark.asyncio
    async def test_system_reminder_set_when_active(self) -> None:
        tool = _make_tool()
        tc = _make_tool_call(
            {
                "todos": [
                    {"id": "t1", "content": "In progress", "status": "in_progress"},
                ],
                "merge": False,
            }
        )

        response = await tool.run(tc)

        assert response.system_reminder != ""
        assert "EXECUTION PHASE" in response.system_reminder

    @pytest.mark.asyncio
    async def test_debug_info_structure(self) -> None:
        tool = _make_tool()
        tc = _make_tool_call(
            {
                "todos": [
                    {"id": "t1", "content": "Task 1", "status": "pending"},
                ],
                "merge": False,
            }
        )

        response = await tool.run(tc)

        assert response.debug_info is not None
        assert "input" in response.debug_info
        assert "state" in response.debug_info
        assert "iteration" in response.debug_info

        state = response.debug_info["state"]
        assert state["total"] == 1
        assert state["pending"] == 1

    @pytest.mark.asyncio
    async def test_invalid_input_returns_error(self) -> None:
        tool = _make_tool()
        tc = _make_tool_call({"invalid": "data"})

        response = await tool.run(tc)

        assert "Error" in response.content
        assert response.system_reminder == ""

    @pytest.mark.asyncio
    async def test_large_list_preserved(self) -> None:
        tool = _make_tool()
        items = [
            {"id": f"t{i}", "content": f"Task {i}", "status": "pending"}
            for i in range(100)
        ]
        tc = _make_tool_call({"todos": items, "merge": False})

        response = await tool.run(tc)

        assert "0/100 completed" in response.content
        assert response.debug_info is not None
        assert response.debug_info["state"]["total"] == 100

    @pytest.mark.asyncio
    async def test_persistence_failure_graceful(self) -> None:
        tool = _make_tool()
        tool._memory_manager.save_async = AsyncMock(
            side_effect=Exception("Backend error")
        )

        tc = _make_tool_call(
            {
                "todos": [{"id": "t1", "content": "Task", "status": "pending"}],
                "merge": False,
            }
        )

        response = await tool.run(tc)

        assert "Task" in response.content
        assert response.system_reminder != ""

    @pytest.mark.asyncio
    async def test_load_failure_uses_cache(self) -> None:
        tool = _make_tool()
        tool._cached_state = TodoList(
            todos=[TodoItem(id="t1", content="Cached", status=TodoStatus.PENDING)]
        )
        tool._memory_manager.load_async = AsyncMock(
            side_effect=Exception("Load failed")
        )

        tc = _make_tool_call(
            {
                "todos": [{"id": "t1", "status": "completed"}],
                "merge": True,
            }
        )

        response = await tool.run(tc)

        assert "[x] Cached" in response.content

    @pytest.mark.asyncio
    async def test_cache_preferred_when_ahead_of_persisted(self) -> None:
        """When cache has a higher iteration than persisted, keep cache."""
        tool = _make_tool()
        tool._cached_state = TodoList(
            todos=[TodoItem(id="t1", content="Cached", status=TodoStatus.IN_PROGRESS)],
            last_updated_iteration=3,
        )
        stale_persisted = TodoList(
            todos=[TodoItem(id="t1", content="Stale", status=TodoStatus.PENDING)],
            last_updated_iteration=1,
        )
        tool._memory_manager.load_async = AsyncMock(return_value=stale_persisted)

        tc = _make_tool_call(
            {
                "todos": [{"id": "t1", "status": "completed"}],
                "merge": True,
            }
        )

        response = await tool.run(tc)

        assert "[x] Cached" in response.content
        assert "Stale" not in response.content


class TestLogStep:
    """Tests for _log_step() Steps panel integration."""

    @pytest.mark.asyncio
    async def test_creates_step_with_display_name_header(self) -> None:
        tool = _make_tool(config=TodoConfig(display_name="Progress"))
        tc = _make_tool_call(
            {
                "todos": [{"id": "t1", "content": "Task", "status": "pending"}],
                "merge": False,
            }
        )

        await tool.run(tc)

        calls = (
            tool._message_step_logger.create_or_update_message_log_async.call_args_list
        )
        assert len(calls) == 2  # plan + progress
        assert calls[0][1]["header"] == "Progress"
        assert calls[1][1]["header"] == "Progress"

    @pytest.mark.asyncio
    async def test_plan_log_shows_numbered_items_with_icons(self) -> None:
        """On first call, _log_step creates a plan entry with status icons."""
        tool = _make_tool()
        tc = _make_tool_call(
            {
                "todos": [
                    {"id": "t1", "content": "Research APIs", "status": "pending"},
                    {"id": "t2", "content": "Write code", "status": "pending"},
                    {"id": "t3", "content": "Write tests", "status": "pending"},
                ],
                "merge": False,
            }
        )

        await tool.run(tc)

        plan_kwargs = (
            tool._message_step_logger.create_or_update_message_log_async.call_args_list[
                0
            ][1]
        )
        expected = (
            "0/3 completed\n○ 1. Research APIs\n○ 2. Write code\n○ 3. Write tests"
        )
        assert plan_kwargs["progress_message"] == expected
        assert plan_kwargs["active_message_log"] is None

    @pytest.mark.asyncio
    async def test_plan_log_updates_icons_on_progress(self) -> None:
        """Plan entry updates with ✓/→/○ as items change status."""
        tool = _make_tool()
        sentinel = MagicMock()
        tool._message_step_logger.create_or_update_message_log_async.return_value = (
            sentinel
        )

        tc1 = _make_tool_call(
            {
                "todos": [
                    {"id": "t1", "content": "Research APIs", "status": "pending"},
                    {"id": "t2", "content": "Write code", "status": "pending"},
                ],
                "merge": False,
            }
        )
        await tool.run(tc1)

        tc2 = _make_tool_call(
            {
                "todos": [
                    {"id": "t1", "status": "completed"},
                    {
                        "id": "t2",
                        "status": "in_progress",
                        "active_form": "Writing code",
                    },
                ],
                "merge": True,
            }
        )
        await tool.run(tc2)

        plan_kwargs = (
            tool._message_step_logger.create_or_update_message_log_async.call_args_list[
                2
            ][1]
        )
        expected = "1/2 completed\n✓ 1. Research APIs\n→ 2. Writing code"
        assert plan_kwargs["progress_message"] == expected
        assert plan_kwargs["active_message_log"] is sentinel

    @pytest.mark.asyncio
    async def test_progress_log_shows_compact_format(self) -> None:
        """Progress entry shows active_form + counts."""
        tool = _make_tool()
        tc = _make_tool_call(
            {
                "todos": [
                    {
                        "id": "t1",
                        "content": "Search docs",
                        "status": "in_progress",
                        "active_form": "Searching documents",
                    },
                    {"id": "t2", "content": "Write report", "status": "pending"},
                ],
                "merge": False,
            }
        )

        await tool.run(tc)

        progress_kwargs = (
            tool._message_step_logger.create_or_update_message_log_async.call_args_list[
                1
            ][1]
        )
        assert (
            progress_kwargs["progress_message"] == "Searching documents (0/2 completed)"
        )

    @pytest.mark.asyncio
    async def test_progress_log_shows_counts_when_no_in_progress(self) -> None:
        """When no item is in_progress, progress entry shows counts only."""
        tool = _make_tool()
        tc = _make_tool_call(
            {
                "todos": [
                    {"id": "t1", "content": "Done", "status": "completed"},
                    {"id": "t2", "content": "Todo", "status": "pending"},
                ],
                "merge": False,
            }
        )

        await tool.run(tc)

        progress_kwargs = (
            tool._message_step_logger.create_or_update_message_log_async.call_args_list[
                1
            ][1]
        )
        assert progress_kwargs["progress_message"] == "1/2 completed"

    @pytest.mark.asyncio
    async def test_progress_log_falls_back_to_content_without_active_form(self) -> None:
        """When in_progress item lacks active_form, progress shows content."""
        tool = _make_tool()
        tc = _make_tool_call(
            {
                "todos": [
                    {"id": "t1", "content": "Search docs", "status": "in_progress"},
                ],
                "merge": False,
            }
        )

        await tool.run(tc)

        progress_kwargs = (
            tool._message_step_logger.create_or_update_message_log_async.call_args_list[
                1
            ][1]
        )
        assert progress_kwargs["progress_message"] == "Search docs (0/1 completed)"

    @pytest.mark.asyncio
    async def test_status_running_when_active_items(self) -> None:
        tool = _make_tool()
        tc = _make_tool_call(
            {
                "todos": [{"id": "t1", "content": "Doing", "status": "in_progress"}],
                "merge": False,
            }
        )

        await tool.run(tc)

        calls = (
            tool._message_step_logger.create_or_update_message_log_async.call_args_list
        )
        for call in calls:
            assert call[1]["status"] == MessageLogStatus.RUNNING

    @pytest.mark.asyncio
    async def test_status_completed_when_all_terminal(self) -> None:
        tool = _make_tool()
        tc = _make_tool_call(
            {
                "todos": [
                    {"id": "t1", "content": "Done", "status": "completed"},
                    {"id": "t2", "content": "Skipped", "status": "cancelled"},
                ],
                "merge": False,
            }
        )

        await tool.run(tc)

        calls = (
            tool._message_step_logger.create_or_update_message_log_async.call_args_list
        )
        for call in calls:
            assert call[1]["status"] == MessageLogStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_plan_log_shows_cancelled_icon(self) -> None:
        """Cancelled items use ✗ icon in the plan entry."""
        tool = _make_tool()
        tc = _make_tool_call(
            {
                "todos": [
                    {"id": "t1", "content": "Dropped", "status": "cancelled"},
                    {"id": "t2", "content": "Done", "status": "completed"},
                ],
                "merge": False,
            }
        )

        await tool.run(tc)

        plan_kwargs = (
            tool._message_step_logger.create_or_update_message_log_async.call_args_list[
                0
            ][1]
        )
        assert "✗ 1. Dropped" in plan_kwargs["progress_message"]
        assert "✓ 2. Done" in plan_kwargs["progress_message"]

    @pytest.mark.asyncio
    async def test_reuses_both_logs_across_calls(self) -> None:
        """Second run() passes both plan and progress logs as active_message_log."""
        tool = _make_tool()
        sentinel = MagicMock()
        tool._message_step_logger.create_or_update_message_log_async.return_value = (
            sentinel
        )

        tc1 = _make_tool_call(
            {
                "todos": [{"id": "t1", "content": "Task", "status": "pending"}],
                "merge": False,
            }
        )
        await tool.run(tc1)

        tc2 = _make_tool_call(
            {"todos": [{"id": "t1", "status": "completed"}], "merge": True}
        )
        await tool.run(tc2)

        calls = (
            tool._message_step_logger.create_or_update_message_log_async.call_args_list
        )
        # 2 calls per run = 4 total
        assert len(calls) == 4
        # Second run's plan call reuses sentinel
        assert calls[2][1]["active_message_log"] is sentinel
        # Second run's progress call reuses sentinel
        assert calls[3][1]["active_message_log"] is sentinel

    @pytest.mark.asyncio
    async def test_log_step_failure_does_not_break_run(self) -> None:
        """_log_step exceptions are swallowed — run() still returns a valid response."""
        tool = _make_tool()
        tool._message_step_logger.create_or_update_message_log_async.side_effect = (
            Exception("Step log broken")
        )

        tc = _make_tool_call(
            {
                "todos": [{"id": "t1", "content": "Task", "status": "pending"}],
                "merge": False,
            }
        )

        response = await tool.run(tc)

        assert "Task" in response.content
        assert response.debug_info is not None


class TestTodoWriteToolConfig:
    def test_tool_registration(self) -> None:
        from unique_toolkit.agentic.tools.factory import ToolFactory

        assert "todo_write" in ToolFactory.tool_map

    def test_default_system_prompt(self) -> None:
        tool = _make_tool()
        prompt = tool.tool_description_for_system_prompt()
        assert prompt == _DEFAULT_SYSTEM_PROMPT
        assert "todo_write" in prompt

    def test_custom_system_prompt(self) -> None:
        config = TodoConfig(system_prompt="Custom system prompt here")
        tool = _make_tool(config=config)
        assert tool.tool_description_for_system_prompt() == "Custom system prompt here"

    def test_default_execution_reminder(self) -> None:
        """Default execution reminder is the built-in prompt."""
        tool = _make_tool()
        assert "EXECUTION PHASE" in tool.config.execution_reminder

    @pytest.mark.asyncio
    async def test_custom_execution_reminder(self) -> None:
        config = TodoConfig(execution_reminder="Custom reminder")
        tool = _make_tool(config=config)

        tc = _make_tool_call(
            {
                "todos": [{"id": "t1", "content": "Task", "status": "pending"}],
                "merge": False,
            }
        )

        response = await tool.run(tc)

        assert response.system_reminder == "Custom reminder"

    def test_tool_description(self) -> None:
        tool = _make_tool()
        desc = tool.tool_description()
        assert desc.name == "todo_write"
        assert "progress" in desc.description.lower()

    def test_evaluation_check_list_empty(self) -> None:
        tool = _make_tool()
        assert tool.evaluation_check_list() == []


class TestMultiStepWorkflow:
    """Scripted conversation simulation testing the full lifecycle."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self) -> None:
        """pending -> in_progress -> completed across multiple iterations."""
        tool = _make_tool()

        # Iteration 1: Create the list
        tc1 = _make_tool_call(
            {
                "todos": [
                    {"id": "research", "content": "Research APIs", "status": "pending"},
                    {"id": "implement", "content": "Write code", "status": "pending"},
                    {"id": "test", "content": "Write tests", "status": "pending"},
                ],
                "merge": False,
            }
        )
        r1 = await tool.run(tc1)
        assert r1.debug_info["state"]["pending"] == 3
        assert r1.system_reminder != ""

        # Iteration 2: Start working
        tc2 = _make_tool_call(
            {
                "todos": [{"id": "research", "status": "in_progress"}],
                "merge": True,
            }
        )
        r2 = await tool.run(tc2)
        assert r2.debug_info["state"]["in_progress"] == 1
        assert r2.debug_info["state"]["pending"] == 2

        # Iteration 3: Complete first, start second
        tc3 = _make_tool_call(
            {
                "todos": [
                    {"id": "research", "status": "completed"},
                    {"id": "implement", "status": "in_progress"},
                ],
                "merge": True,
            }
        )
        r3 = await tool.run(tc3)
        assert r3.debug_info["state"]["completed"] == 1
        assert r3.debug_info["state"]["in_progress"] == 1

        # Iteration 4: Complete all
        tc4 = _make_tool_call(
            {
                "todos": [
                    {"id": "implement", "status": "completed"},
                    {"id": "test", "status": "completed"},
                ],
                "merge": True,
            }
        )
        r4 = await tool.run(tc4)
        assert r4.debug_info["state"]["completed"] == 3
        assert r4.debug_info["state"]["pending"] == 0
        assert r4.system_reminder == ""

    @pytest.mark.asyncio
    async def test_mid_conversation_additions(self) -> None:
        """New items can be added mid-conversation via merge."""
        tool = _make_tool()

        tc1 = _make_tool_call(
            {
                "todos": [
                    {"id": "step1", "content": "Step 1", "status": "in_progress"},
                ],
                "merge": False,
            }
        )
        await tool.run(tc1)

        tc2 = _make_tool_call(
            {
                "todos": [
                    {"id": "step1", "status": "completed"},
                    {
                        "id": "step2",
                        "content": "Step 2 (added later)",
                        "status": "pending",
                    },
                ],
                "merge": True,
            }
        )
        r2 = await tool.run(tc2)
        assert r2.debug_info["state"]["total"] == 2
        assert "Step 2 (added later)" in r2.content

    @pytest.mark.asyncio
    async def test_replace_resets_list(self) -> None:
        """merge=False replaces the entire list."""
        tool = _make_tool()

        tc1 = _make_tool_call(
            {
                "todos": [
                    {"id": "old", "content": "Old task", "status": "completed"},
                ],
                "merge": False,
            }
        )
        await tool.run(tc1)

        tc2 = _make_tool_call(
            {
                "todos": [
                    {"id": "new", "content": "New task", "status": "pending"},
                ],
                "merge": False,
            }
        )
        r2 = await tool.run(tc2)
        assert r2.debug_info["state"]["total"] == 1
        assert "New task" in r2.content
        assert "Old task" not in r2.content

    @pytest.mark.asyncio
    async def test_iteration_counter_increments(self) -> None:
        tool = _make_tool()

        tc1 = _make_tool_call(
            {
                "todos": [{"id": "t1", "content": "x", "status": "pending"}],
                "merge": False,
            }
        )
        r1 = await tool.run(tc1)
        assert r1.debug_info["iteration"] == 1

        tc2 = _make_tool_call(
            {
                "todos": [{"id": "t1", "status": "completed"}],
                "merge": True,
            }
        )
        r2 = await tool.run(tc2)
        assert r2.debug_info["iteration"] == 2


class TestVerificationNudge:
    """Tests for _maybe_add_verification_nudge behavior."""

    @pytest.mark.asyncio
    async def test_no_nudge_when_threshold_zero(self) -> None:
        tool = _make_tool(config=TodoConfig(verification_threshold=0))
        tc = _make_tool_call(
            {
                "todos": [
                    {"id": "t1", "content": "Done", "status": "completed"},
                    {"id": "t2", "content": "Done 2", "status": "completed"},
                    {"id": "t3", "content": "Todo", "status": "pending"},
                ],
                "merge": False,
            }
        )

        response = await tool.run(tc)
        assert "[Checkpoint" not in response.content

    @pytest.mark.asyncio
    async def test_nudge_fires_at_threshold(self) -> None:
        tool = _make_tool(config=TodoConfig(verification_threshold=2))
        tc = _make_tool_call(
            {
                "todos": [
                    {"id": "t1", "content": "Done", "status": "completed"},
                    {"id": "t2", "content": "Done 2", "status": "completed"},
                    {"id": "t3", "content": "Todo", "status": "pending"},
                ],
                "merge": False,
            }
        )

        response = await tool.run(tc)
        assert "[Checkpoint: 2 tasks completed" in response.content

    @pytest.mark.asyncio
    async def test_no_nudge_when_all_completed(self) -> None:
        """No nudge when there are no pending items left."""
        tool = _make_tool(config=TodoConfig(verification_threshold=2))
        tc = _make_tool_call(
            {
                "todos": [
                    {"id": "t1", "content": "Done", "status": "completed"},
                    {"id": "t2", "content": "Done 2", "status": "completed"},
                ],
                "merge": False,
            }
        )

        response = await tool.run(tc)
        assert "[Checkpoint" not in response.content

    @pytest.mark.asyncio
    async def test_no_nudge_below_threshold(self) -> None:
        tool = _make_tool(config=TodoConfig(verification_threshold=3))
        tc = _make_tool_call(
            {
                "todos": [
                    {"id": "t1", "content": "Done", "status": "completed"},
                    {"id": "t2", "content": "Done 2", "status": "completed"},
                    {"id": "t3", "content": "Todo", "status": "pending"},
                ],
                "merge": False,
            }
        )

        response = await tool.run(tc)
        assert "[Checkpoint" not in response.content


class TestParallelModeConfig:
    """Tests for parallel_mode toggling descriptions and reminders."""

    def test_default_is_sequential(self) -> None:
        config = TodoConfig()
        assert config.parallel_mode is False

    def test_sequential_tool_description(self) -> None:
        config = TodoConfig(parallel_mode=False)
        assert config.effective_tool_description == _DEFAULT_TOOL_DESCRIPTION

    def test_parallel_tool_description(self) -> None:
        config = TodoConfig(parallel_mode=True)
        assert config.effective_tool_description == _PARALLEL_TOOL_DESCRIPTION

    def test_sequential_execution_reminder(self) -> None:
        config = TodoConfig(parallel_mode=False)
        assert "Mark exactly one item" in config.effective_execution_reminder

    def test_parallel_execution_reminder(self) -> None:
        config = TodoConfig(parallel_mode=True)
        assert config.effective_execution_reminder == _PARALLEL_EXECUTION_REMINDER

    @pytest.mark.asyncio
    async def test_tool_uses_effective_description(self) -> None:
        tool = _make_tool(config=TodoConfig(parallel_mode=True))
        desc = tool.tool_description()
        assert desc.description == _PARALLEL_TOOL_DESCRIPTION

    @pytest.mark.asyncio
    async def test_tool_uses_effective_system_prompt(self) -> None:
        tool = _make_tool(config=TodoConfig(parallel_mode=True))
        prompt = tool.tool_description_for_system_prompt()
        assert "parallel" in prompt.lower()

    @pytest.mark.asyncio
    async def test_tool_uses_effective_reminder_in_response(self) -> None:
        tool = _make_tool(config=TodoConfig(parallel_mode=True))
        tc = _make_tool_call(
            {
                "todos": [
                    {"id": "t1", "content": "Task", "status": "in_progress"},
                ],
                "merge": False,
            }
        )

        response = await tool.run(tc)
        assert response.system_reminder == _PARALLEL_EXECUTION_REMINDER

    def test_parallel_mode_appends_rules_when_prompt_customized(self) -> None:
        """When system_prompt is customized and no longer contains the
        sequential rules substring, parallel execution rules are appended."""
        custom_prompt = "You are a helpful assistant. Do your best."
        config = TodoConfig(parallel_mode=True, system_prompt=custom_prompt)
        result = config.effective_system_prompt
        assert custom_prompt in result
        assert _PARALLEL_EXECUTION_RULES.strip() in result

    def test_parallel_mode_preserves_custom_tool_description(self) -> None:
        custom = "My custom tool description."
        config = TodoConfig(parallel_mode=True, tool_description=custom)
        assert config.effective_tool_description == custom

    def test_parallel_mode_preserves_custom_execution_reminder(self) -> None:
        custom = "My custom reminder."
        config = TodoConfig(parallel_mode=True, execution_reminder=custom)
        assert config.effective_execution_reminder == custom
