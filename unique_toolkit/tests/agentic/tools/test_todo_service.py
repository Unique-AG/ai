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

from unique_toolkit._common.utils.jinja.render import render_template
from unique_toolkit.agentic.tools.experimental.todo.config import TodoConfig
from unique_toolkit.agentic.tools.experimental.todo.prompts import (
    EXECUTION_REMINDER_TEMPLATE,
    SYSTEM_PROMPT_TEMPLATE,
    TOOL_DESCRIPTION_TEMPLATE,
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
    if "TodoWrite" not in ToolFactory.tool_config_map:
        ToolFactory.register_tool(TodoWriteTool, TodoConfig)
    yield


def _item_with_default_active_form_none(
    id: str,
    content: str,
    status: TodoStatus,
    active_form: str | None = None,
) -> TodoItem:
    return TodoItem(id=id, content=content, status=status, active_form=active_form)


def _item_input_with_default_active_form_and_content_none(
    id: str,
    status: TodoStatus,
    content: str | None = None,
    active_form: str | None = None,
) -> TodoItemInput:
    return TodoItemInput(id=id, content=content, status=status, active_form=active_form)


def _todo_list_with_default_none_list_and_zero_iteration(
    todos: list[TodoItem] | None = None,
    last_updated_iteration: int = 0,
) -> TodoList:
    return TodoList(todos=todos or [], last_updated_iteration=last_updated_iteration)


class TestTodoList:
    def test_empty_format(self) -> None:
        tl = _todo_list_with_default_none_list_and_zero_iteration()
        assert tl.format() == "No tasks tracked."

    def test_format_with_items(self) -> None:
        tl = _todo_list_with_default_none_list_and_zero_iteration(
            todos=[
                _item_with_default_active_form_none("a", "Task A", TodoStatus.PENDING),
                _item_with_default_active_form_none(
                    "b", "Task B", TodoStatus.COMPLETED
                ),
            ]
        )
        formatted = tl.format()
        assert "1/2 completed" in formatted
        assert "[ ] Task A" in formatted
        assert "[x] Task B" in formatted

    def test_has_active_items_with_pending(self) -> None:
        tl = _todo_list_with_default_none_list_and_zero_iteration(
            todos=[_item_with_default_active_form_none("a", "x", TodoStatus.PENDING)]
        )
        assert tl.has_active_items() is True

    def test_has_active_items_with_in_progress(self) -> None:
        tl = _todo_list_with_default_none_list_and_zero_iteration(
            todos=[
                _item_with_default_active_form_none("a", "x", TodoStatus.IN_PROGRESS)
            ]
        )
        assert tl.has_active_items() is True

    def test_has_active_items_all_completed(self) -> None:
        tl = _todo_list_with_default_none_list_and_zero_iteration(
            todos=[_item_with_default_active_form_none("a", "x", TodoStatus.COMPLETED)]
        )
        assert tl.has_active_items() is False

    def test_has_active_items_all_cancelled(self) -> None:
        tl = _todo_list_with_default_none_list_and_zero_iteration(
            todos=[_item_with_default_active_form_none("a", "x", TodoStatus.CANCELLED)]
        )
        assert tl.has_active_items() is False

    def test_has_active_items_empty(self) -> None:
        tl = _todo_list_with_default_none_list_and_zero_iteration()
        assert tl.has_active_items() is False

    def test_status_counts(self) -> None:
        tl = _todo_list_with_default_none_list_and_zero_iteration(
            todos=[
                _item_with_default_active_form_none("a", "x", TodoStatus.PENDING),
                _item_with_default_active_form_none("b", "x", TodoStatus.IN_PROGRESS),
                _item_with_default_active_form_none("c", "x", TodoStatus.COMPLETED),
                _item_with_default_active_form_none("d", "x", TodoStatus.CANCELLED),
                _item_with_default_active_form_none("e", "x", TodoStatus.PENDING),
            ]
        )
        counts = tl.status_counts()
        assert counts["pending"] == 2
        assert counts["in_progress"] == 1
        assert counts["completed"] == 1
        assert counts["cancelled"] == 1
        assert counts["total"] == 5


class TestTodoListUpdate:
    def test_update_existing_item(self) -> None:
        tl = _todo_list_with_default_none_list_and_zero_iteration(
            todos=[
                _item_with_default_active_form_none("a", "Task A", TodoStatus.PENDING)
            ]
        )
        updated = tl.update(
            [
                _item_input_with_default_active_form_and_content_none(
                    "a", TodoStatus.COMPLETED, active_form=None
                )
            ]
        )
        assert updated.todos[0].status == TodoStatus.COMPLETED
        assert updated.todos[0].content == "Task A"

    def test_append_new_item(self) -> None:
        tl = _todo_list_with_default_none_list_and_zero_iteration(
            todos=[
                _item_with_default_active_form_none("a", "Task A", TodoStatus.PENDING)
            ]
        )
        updated = tl.update(
            [
                _item_input_with_default_active_form_and_content_none(
                    "b", TodoStatus.PENDING, content="Task B"
                )
            ]
        )
        assert len(updated.todos) == 2
        assert updated.todos[1].id == "b"

    def test_preserve_unmentioned(self) -> None:
        tl = _todo_list_with_default_none_list_and_zero_iteration(
            todos=[
                _item_with_default_active_form_none("a", "Task A", TodoStatus.PENDING),
                _item_with_default_active_form_none("b", "Task B", TodoStatus.PENDING),
            ]
        )
        updated = tl.update(
            [
                _item_input_with_default_active_form_and_content_none(
                    "a", TodoStatus.COMPLETED, active_form=None
                )
            ]
        )
        assert len(updated.todos) == 2
        assert updated.todos[0].status == TodoStatus.COMPLETED
        assert updated.todos[1].status == TodoStatus.PENDING

    def test_update_preserves_content_when_omitted(self) -> None:
        tl = _todo_list_with_default_none_list_and_zero_iteration(
            todos=[
                _item_with_default_active_form_none("a", "Original", TodoStatus.PENDING)
            ]
        )
        updated = tl.update(
            [
                _item_input_with_default_active_form_and_content_none(
                    "a", TodoStatus.IN_PROGRESS, content=None
                )
            ]
        )
        assert updated.todos[0].content == "Original"

    def test_new_item_without_content_gets_empty_string(self) -> None:
        tl = _todo_list_with_default_none_list_and_zero_iteration()
        updated = tl.update(
            [
                _item_input_with_default_active_form_and_content_none(
                    "a", TodoStatus.PENDING, content=None
                )
            ]
        )
        assert updated.todos[0].content == ""

    def test_update_preserves_iteration_counter(self) -> None:
        tl = _todo_list_with_default_none_list_and_zero_iteration(
            last_updated_iteration=5
        )
        updated = tl.update(
            [
                _item_input_with_default_active_form_and_content_none(
                    "a", TodoStatus.PENDING, content="x"
                )
            ]
        )
        assert updated.last_updated_iteration == 5

    def test_update_preserves_active_form_when_omitted(self) -> None:
        tl = _todo_list_with_default_none_list_and_zero_iteration(
            todos=[
                _item_with_default_active_form_none(
                    "a",
                    "Task A",
                    TodoStatus.PENDING,
                    active_form="Doing Task A",
                )
            ]
        )
        updated = tl.update(
            [
                _item_input_with_default_active_form_and_content_none(
                    "a", TodoStatus.IN_PROGRESS, active_form=None
                )
            ]
        )
        assert updated.todos[0].active_form == "Doing Task A"

    def test_update_overwrites_active_form_when_supplied(self) -> None:
        tl = _todo_list_with_default_none_list_and_zero_iteration(
            todos=[
                _item_with_default_active_form_none(
                    "a",
                    "Task A",
                    TodoStatus.PENDING,
                    active_form="Old form",
                )
            ]
        )
        updated = tl.update(
            [
                _item_input_with_default_active_form_and_content_none(
                    "a", TodoStatus.IN_PROGRESS, active_form="New form"
                )
            ]
        )
        assert updated.todos[0].active_form == "New form"

    def test_new_item_without_active_form_is_none(self) -> None:
        tl = _todo_list_with_default_none_list_and_zero_iteration()
        updated = tl.update(
            [
                _item_input_with_default_active_form_and_content_none(
                    "a", TodoStatus.PENDING, content="x"
                )
            ]
        )
        assert updated.todos[0].active_form is None


class TestTodoWriteInput:
    def test_min_length_validation(self) -> None:
        with pytest.raises(Exception):
            TodoWriteInput(todos=[], merge=True)

    def test_merge_field_required(self) -> None:
        inp = TodoWriteInput(
            todos=[
                TodoItemInput(
                    id="a",
                    content="x",
                    status=TodoStatus.PENDING,
                    active_form=None,
                )
            ],
            merge=True,
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


def _tc_item(
    id: str,
    status: str,
    content: str | None = None,
    active_form: str | None = None,
) -> dict:
    """Build a tool-call todo item dict with all required fields."""
    return {
        "id": id,
        "content": content,
        "status": status,
        "active_form": active_form,
    }


class TestTodoWriteTool:
    @pytest.mark.asyncio
    async def test_create_new_list(self) -> None:
        tool = _make_tool()
        tc = _make_tool_call(
            {
                "todos": [
                    _tc_item("t1", "pending", content="Research APIs"),
                    _tc_item("t2", "pending", content="Write code"),
                ],
                "merge": False,
            }
        )

        response = await tool.run(tc)

        assert response.name == "TodoWrite"
        assert "Research APIs" in response.content
        assert "Write code" in response.content
        assert "0/2 completed" in response.content
        assert response.system_reminder != ""

    @pytest.mark.asyncio
    async def test_merge_updates_existing(self) -> None:
        tool = _make_tool()
        tool._cached_state = _todo_list_with_default_none_list_and_zero_iteration(
            todos=[
                _item_with_default_active_form_none(
                    "t1", "Research APIs", TodoStatus.PENDING
                )
            ],
            last_updated_iteration=0,
        )
        tool._memory_manager.load_async = AsyncMock(return_value=None)

        tc = _make_tool_call(
            {
                "todos": [_tc_item("t1", "completed")],
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
                    _tc_item("t1", "completed", content="Done"),
                    _tc_item("t2", "cancelled", content="Skipped"),
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
                    _tc_item("t1", "in_progress", content="In progress"),
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
                    _tc_item("t1", "pending", content="Task 1"),
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
        items = [_tc_item(f"t{i}", "pending", content=f"Task {i}") for i in range(100)]
        tc = _make_tool_call({"todos": items, "merge": False})

        response = await tool.run(tc)

        assert "0/100 completed" in response.content
        assert response.debug_info is not None
        assert response.debug_info["state"]["pending"] == 100

    @pytest.mark.asyncio
    async def test_persistence_failure_graceful(self) -> None:
        tool = _make_tool()
        tool._memory_manager.save_async = AsyncMock(
            side_effect=Exception("Backend error")
        )

        tc = _make_tool_call(
            {
                "todos": [_tc_item("t1", "pending", content="Task")],
                "merge": False,
            }
        )

        response = await tool.run(tc)

        assert "Task" in response.content
        assert response.system_reminder != ""

    @pytest.mark.asyncio
    async def test_load_failure_uses_cache(self) -> None:
        tool = _make_tool()
        tool._cached_state = _todo_list_with_default_none_list_and_zero_iteration(
            todos=[
                _item_with_default_active_form_none("t1", "Cached", TodoStatus.PENDING)
            ]
        )
        tool._memory_manager.load_async = AsyncMock(
            side_effect=Exception("Load failed")
        )

        tc = _make_tool_call(
            {
                "todos": [_tc_item("t1", "completed")],
                "merge": True,
            }
        )

        response = await tool.run(tc)

        assert "[x] Cached" in response.content

    @pytest.mark.asyncio
    async def test_cache_preferred_when_ahead_of_persisted(self) -> None:
        """When cache has a higher iteration than persisted, keep cache."""
        tool = _make_tool()
        tool._cached_state = _todo_list_with_default_none_list_and_zero_iteration(
            todos=[
                _item_with_default_active_form_none(
                    "t1", "Cached", TodoStatus.IN_PROGRESS
                )
            ],
            last_updated_iteration=3,
        )
        stale_persisted = _todo_list_with_default_none_list_and_zero_iteration(
            todos=[
                _item_with_default_active_form_none("t1", "Stale", TodoStatus.PENDING)
            ],
            last_updated_iteration=1,
        )
        tool._memory_manager.load_async = AsyncMock(return_value=stale_persisted)

        tc = _make_tool_call(
            {
                "todos": [_tc_item("t1", "completed")],
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
                "todos": [_tc_item("t1", "pending", content="Task")],
                "merge": False,
            }
        )

        await tool.run(tc)

        calls = (
            tool._message_step_logger.create_or_update_message_log_async.call_args_list
        )
        assert len(calls) == 1
        assert calls[0][1]["header"] == "Progress"

    @pytest.mark.asyncio
    async def test_plan_log_shows_numbered_items_with_icons(self) -> None:
        """On first call, _log_step creates a plan entry with status icons."""
        tool = _make_tool()
        tc = _make_tool_call(
            {
                "todos": [
                    _tc_item("t1", "pending", content="Research APIs"),
                    _tc_item("t2", "pending", content="Write code"),
                    _tc_item("t3", "pending", content="Write tests"),
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
                    _tc_item("t1", "pending", content="Research APIs"),
                    _tc_item("t2", "pending", content="Write code"),
                ],
                "merge": False,
            }
        )
        await tool.run(tc1)

        tc2 = _make_tool_call(
            {
                "todos": [
                    _tc_item("t1", "completed"),
                    _tc_item("t2", "in_progress", active_form="Writing code"),
                ],
                "merge": True,
            }
        )
        await tool.run(tc2)

        plan_kwargs = (
            tool._message_step_logger.create_or_update_message_log_async.call_args_list[
                1
            ][1]
        )
        expected = "1/2 completed\n✓ 1. Research APIs\n→ 2. Writing code"
        assert plan_kwargs["progress_message"] == expected
        assert plan_kwargs["active_message_log"] is sentinel

    @pytest.mark.asyncio
    async def test_status_running_when_active_items(self) -> None:
        tool = _make_tool()
        tc = _make_tool_call(
            {
                "todos": [
                    _tc_item("t1", "in_progress", content="Doing"),
                ],
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
                    _tc_item("t1", "completed", content="Done"),
                    _tc_item("t2", "cancelled", content="Skipped"),
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
                    _tc_item("t1", "cancelled", content="Dropped"),
                    _tc_item("t2", "completed", content="Done"),
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
    async def test_reuses_plan_log_across_calls(self) -> None:
        """Second run() passes the plan log as active_message_log."""
        tool = _make_tool()
        sentinel = MagicMock()
        tool._message_step_logger.create_or_update_message_log_async.return_value = (
            sentinel
        )

        tc1 = _make_tool_call(
            {
                "todos": [_tc_item("t1", "pending", content="Task")],
                "merge": False,
            }
        )
        await tool.run(tc1)

        tc2 = _make_tool_call(
            {
                "todos": [_tc_item("t1", "completed")],
                "merge": True,
            }
        )
        await tool.run(tc2)

        calls = (
            tool._message_step_logger.create_or_update_message_log_async.call_args_list
        )
        assert len(calls) == 2
        assert calls[1][1]["active_message_log"] is sentinel

    @pytest.mark.asyncio
    async def test_log_step_failure_does_not_break_run(self) -> None:
        """_log_step exceptions are swallowed — run() still returns a valid response."""
        tool = _make_tool()
        tool._message_step_logger.create_or_update_message_log_async.side_effect = (
            Exception("Step log broken")
        )

        tc = _make_tool_call(
            {
                "todos": [_tc_item("t1", "pending", content="Task")],
                "merge": False,
            }
        )

        response = await tool.run(tc)

        assert "Task" in response.content
        assert response.debug_info is not None


class TestTodoWriteToolConfig:
    def test_tool_registration(self) -> None:
        from unique_toolkit.agentic.tools.factory import ToolFactory

        assert "TodoWrite" in ToolFactory.tool_map

    def test_default_system_prompt(self) -> None:
        tool = _make_tool()
        prompt = tool.tool_description_for_system_prompt()
        expected = render_template(SYSTEM_PROMPT_TEMPLATE, parallel_mode=False)
        assert prompt == expected
        assert "TodoWrite" in prompt

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
                "todos": [_tc_item("t1", "pending", content="Task")],
                "merge": False,
            }
        )

        response = await tool.run(tc)

        assert response.system_reminder == "Custom reminder"

    def test_tool_description(self) -> None:
        tool = _make_tool()
        desc = tool.tool_description()
        assert desc.name == "TodoWrite"
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
                    _tc_item("research", "pending", content="Research APIs"),
                    _tc_item("implement", "pending", content="Write code"),
                    _tc_item("test", "pending", content="Write tests"),
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
                "todos": [_tc_item("research", "in_progress")],
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
                    _tc_item("research", "completed"),
                    _tc_item("implement", "in_progress"),
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
                    _tc_item("implement", "completed"),
                    _tc_item("test", "completed"),
                ],
                "merge": True,
            }
        )
        r4 = await tool.run(tc4)
        assert r4.debug_info["state"]["completed"] == 3
        assert r4.system_reminder == ""

    @pytest.mark.asyncio
    async def test_mid_conversation_additions(self) -> None:
        """New items can be added mid-conversation via merge."""
        tool = _make_tool()

        tc1 = _make_tool_call(
            {
                "todos": [
                    _tc_item("step1", "in_progress", content="Step 1"),
                ],
                "merge": False,
            }
        )
        await tool.run(tc1)

        tc2 = _make_tool_call(
            {
                "todos": [
                    _tc_item("step1", "completed"),
                    _tc_item("step2", "pending", content="Step 2 (added later)"),
                ],
                "merge": True,
            }
        )
        r2 = await tool.run(tc2)
        assert len(r2.debug_info["state"]["items"]) == 2
        assert "Step 2 (added later)" in r2.content

    @pytest.mark.asyncio
    async def test_replace_resets_list(self) -> None:
        """merge=False replaces the entire list."""
        tool = _make_tool()

        tc1 = _make_tool_call(
            {
                "todos": [
                    _tc_item("old", "completed", content="Old task"),
                ],
                "merge": False,
            }
        )
        await tool.run(tc1)

        tc2 = _make_tool_call(
            {
                "todos": [
                    _tc_item("new", "pending", content="New task"),
                ],
                "merge": False,
            }
        )
        r2 = await tool.run(tc2)
        assert len(r2.debug_info["state"]["items"]) == 1
        assert "New task" in r2.content
        assert "Old task" not in r2.content

    @pytest.mark.asyncio
    async def test_iteration_counter_increments(self) -> None:
        tool = _make_tool()

        tc1 = _make_tool_call(
            {
                "todos": [_tc_item("t1", "pending", content="x")],
                "merge": False,
            }
        )
        r1 = await tool.run(tc1)
        assert r1.debug_info["iteration"] == 1

        tc2 = _make_tool_call(
            {
                "todos": [_tc_item("t1", "completed")],
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
                    _tc_item("t1", "completed", content="Done"),
                    _tc_item("t2", "completed", content="Done 2"),
                    _tc_item("t3", "pending", content="Todo"),
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
                    _tc_item("t1", "completed", content="Done"),
                    _tc_item("t2", "completed", content="Done 2"),
                    _tc_item("t3", "pending", content="Todo"),
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
                    _tc_item("t1", "completed", content="Done"),
                    _tc_item("t2", "completed", content="Done 2"),
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
                    _tc_item("t1", "completed", content="Done"),
                    _tc_item("t2", "completed", content="Done 2"),
                    _tc_item("t3", "pending", content="Todo"),
                ],
                "merge": False,
            }
        )

        response = await tool.run(tc)
        assert "[Checkpoint" not in response.content


class TestParallelModeConfig:
    """Tests for parallel_mode toggling descriptions and reminders via Jinja templates."""

    def test_default_is_sequential(self) -> None:
        config = TodoConfig()
        assert config.parallel_mode is False

    def test_sequential_tool_description(self) -> None:
        tool = _make_tool(config=TodoConfig(parallel_mode=False))
        desc = tool.tool_description()
        expected = render_template(TOOL_DESCRIPTION_TEMPLATE, parallel_mode=False)
        assert desc.description == expected
        assert "Mark exactly one item" in desc.description

    def test_parallel_tool_description(self) -> None:
        tool = _make_tool(config=TodoConfig(parallel_mode=True))
        desc = tool.tool_description()
        expected = render_template(TOOL_DESCRIPTION_TEMPLATE, parallel_mode=True)
        assert desc.description == expected
        assert "multiple items in_progress" in desc.description

    def test_sequential_execution_reminder(self) -> None:
        rendered = render_template(EXECUTION_REMINDER_TEMPLATE, parallel_mode=False)
        assert "Mark exactly one item" in rendered
        assert "TodoWrite call alongside" not in rendered

    def test_parallel_execution_reminder(self) -> None:
        rendered = render_template(EXECUTION_REMINDER_TEMPLATE, parallel_mode=True)
        assert "TodoWrite call alongside" in rendered
        assert "Mark exactly one item" not in rendered

    def test_tool_uses_parallel_description(self) -> None:
        tool = _make_tool(config=TodoConfig(parallel_mode=True))
        desc = tool.tool_description()
        expected = render_template(TOOL_DESCRIPTION_TEMPLATE, parallel_mode=True)
        assert desc.description == expected

    def test_tool_uses_parallel_system_prompt(self) -> None:
        tool = _make_tool(config=TodoConfig(parallel_mode=True))
        prompt = tool.tool_description_for_system_prompt()
        assert "Mark multiple items in_progress simultaneously" in prompt
        assert "Mark exactly ONE item" not in prompt

    @pytest.mark.asyncio
    async def test_tool_uses_parallel_reminder_in_response(self) -> None:
        tool = _make_tool(config=TodoConfig(parallel_mode=True))
        tc = _make_tool_call(
            {
                "todos": [
                    _tc_item("t1", "in_progress", content="Task"),
                ],
                "merge": False,
            }
        )

        response = await tool.run(tc)
        expected = render_template(EXECUTION_REMINDER_TEMPLATE, parallel_mode=True)
        assert response.system_reminder == expected

    def test_custom_prompt_rendered_as_jinja(self) -> None:
        """Custom templates with Jinja syntax are rendered with parallel_mode."""
        custom = "Mode: {% if parallel_mode %}parallel{% else %}sequential{% endif %}"
        config = TodoConfig(parallel_mode=True, system_prompt=custom)
        tool = _make_tool(config=config)
        assert tool.tool_description_for_system_prompt() == "Mode: parallel"

    def test_custom_tool_description_rendered(self) -> None:
        custom = "My custom tool description."
        tool = _make_tool(
            config=TodoConfig(parallel_mode=True, tool_description=custom)
        )
        desc = tool.tool_description()
        assert desc.description == custom

    @pytest.mark.asyncio
    async def test_custom_execution_reminder_rendered(self) -> None:
        custom = "My custom reminder."
        tool = _make_tool(
            config=TodoConfig(parallel_mode=True, execution_reminder=custom)
        )
        tc = _make_tool_call(
            {
                "todos": [
                    _tc_item("t1", "pending", content="Task"),
                ],
                "merge": False,
            }
        )

        response = await tool.run(tc)
        assert response.system_reminder == custom
