"""Tests for TodoWriteTool, TodoList, and related schemas.

Covers:
- TodoList.update() logic (update, append, preserve)
- TodoList.has_active_items() logic
- TodoList.status_counts() aggregation
- TodoWriteTool.run() (create, update, replace, formatting)
- Large todo lists (100 items) preserved without truncation
- debug_info structure on tool response
- system_reminder set when active items, empty when all terminal
- _log_step() Steps panel integration
- Tool registration, config validation
- Configurable prompts via TodoConfig
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_toolkit.agentic.tools.experimental.todo.config import (
    _DEFAULT_SYSTEM_PROMPT,
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

        tool._message_step_logger.create_or_update_message_log.assert_called_once()
        call_kwargs = tool._message_step_logger.create_or_update_message_log.call_args[
            1
        ]
        assert call_kwargs["header"] == "Progress"

    @pytest.mark.asyncio
    async def test_progress_message_contains_counts(self) -> None:
        tool = _make_tool()
        tc = _make_tool_call(
            {
                "todos": [
                    {"id": "t1", "content": "Done", "status": "completed"},
                    {"id": "t2", "content": "Doing", "status": "in_progress"},
                    {"id": "t3", "content": "Todo", "status": "pending"},
                ],
                "merge": False,
            }
        )

        await tool.run(tc)

        call_kwargs = tool._message_step_logger.create_or_update_message_log.call_args[
            1
        ]
        progress = call_kwargs["progress_message"]
        assert "3 items" in progress
        assert "1 completed" in progress
        assert "1 in_progress" in progress
        assert "1 pending" in progress

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

        call_kwargs = tool._message_step_logger.create_or_update_message_log.call_args[
            1
        ]
        assert call_kwargs["status"] == MessageLogStatus.RUNNING

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

        call_kwargs = tool._message_step_logger.create_or_update_message_log.call_args[
            1
        ]
        assert call_kwargs["status"] == MessageLogStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_reuses_message_log_across_calls(self) -> None:
        """Second run() passes the MessageLog from the first call as active_message_log."""
        tool = _make_tool()
        sentinel = MagicMock()
        tool._message_step_logger.create_or_update_message_log.return_value = sentinel

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

        second_call_kwargs = (
            tool._message_step_logger.create_or_update_message_log.call_args_list[1][1]
        )
        assert second_call_kwargs["active_message_log"] is sentinel

    @pytest.mark.asyncio
    async def test_log_step_failure_does_not_break_run(self) -> None:
        """_log_step exceptions are swallowed — run() still returns a valid response."""
        tool = _make_tool()
        tool._message_step_logger.create_or_update_message_log.side_effect = Exception(
            "Step log broken"
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
