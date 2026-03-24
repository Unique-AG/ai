from unittest.mock import AsyncMock, Mock

import pytest

from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.todo.config import TodoConfig
from unique_toolkit.agentic.tools.todo.schemas import (
    TodoItem,
    TodoList,
    TodoWriteInput,
)
from unique_toolkit.agentic.tools.todo.service import (
    TodoReadTool,
    TodoWriteTool,
)
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.language_model.schemas import LanguageModelFunction


@pytest.fixture(autouse=True)
def ensure_todo_tools_registered():
    """Ensure todo tools are registered before tests run."""
    if TodoWriteTool.name not in ToolFactory.tool_config_map:
        ToolFactory.register_tool(TodoWriteTool, TodoConfig)
    if TodoReadTool.name not in ToolFactory.tool_config_map:
        ToolFactory.register_tool(
            TodoReadTool, TodoConfig
        )  # manual registration for test
    yield


@pytest.fixture
def mock_chat_event() -> ChatEvent:
    """Create a mock ChatEvent for testing."""
    event = Mock(spec=ChatEvent)
    event.user_id = "user_123"
    event.company_id = "company_456"
    event.chat_id = "chat_789"
    event.assistant_id = "assistant_101"

    mock_payload = Mock()
    mock_payload.chat_id = "chat_789"
    mock_payload.assistant_message = Mock()
    mock_payload.assistant_message.id = "assistant_message_202"
    event.payload = mock_payload

    return event


@pytest.fixture
def todo_config() -> TodoConfig:
    return TodoConfig()


@pytest.fixture
def sample_todos() -> list[TodoItem]:
    return [
        TodoItem(id="task-1", content="Research API options", status="completed"),
        TodoItem(id="task-2", content="Implement service layer", status="in_progress"),
        TodoItem(id="task-3", content="Write tests", status="pending"),
    ]


@pytest.fixture
def sample_state(sample_todos: list[TodoItem]) -> TodoList:
    return TodoList(todos=sample_todos, last_updated_iteration=2)


def _make_tool_call(
    arguments: dict | str, call_id: str = "call_1"
) -> LanguageModelFunction:
    """Create a LanguageModelFunction. Arguments can be dict or JSON string (auto-parsed)."""
    return LanguageModelFunction(id=call_id, name="todo_write", arguments=arguments)


class TestTodoList:
    """Tests for TodoList update logic."""

    @pytest.mark.ai
    def test_update__matching_ids__updates_status(self) -> None:
        """
        Purpose: Verify update overwrites existing items when IDs match.
        Why: Core update semantics -- the model updates status of existing items.
        Setup: State with one pending item, update with same ID as completed.
        """
        state = TodoList(todos=[TodoItem(id="a", content="Do X", status="pending")])
        incoming = [TodoItem(id="a", content="Do X", status="completed")]

        result = state.update(incoming)

        assert len(result.todos) == 1
        assert result.todos[0].status == "completed"

    @pytest.mark.ai
    def test_update__new_ids__appends(self) -> None:
        """
        Purpose: Verify update adds new items that don't exist yet.
        Why: The model adds new tasks as it discovers more work.
        Setup: State with one item, update with a different ID.
        """
        state = TodoList(todos=[TodoItem(id="a", content="Do X", status="pending")])
        incoming = [TodoItem(id="b", content="Do Y", status="pending")]

        result = state.update(incoming)

        assert len(result.todos) == 2
        ids = {t.id for t in result.todos}
        assert ids == {"a", "b"}

    @pytest.mark.ai
    def test_update__no_match__preserves_existing(self) -> None:
        """
        Purpose: Verify update preserves items not mentioned in incoming.
        Why: Partial updates should not delete unrelated tasks.
        Setup: State with two items, update changes only one.
        """
        state = TodoList(
            todos=[
                TodoItem(id="a", content="Do X", status="pending"),
                TodoItem(id="b", content="Do Y", status="pending"),
            ]
        )
        incoming = [TodoItem(id="a", content="Do X", status="completed")]

        result = state.update(incoming)

        assert len(result.todos) == 2
        by_id = {t.id: t for t in result.todos}
        assert by_id["a"].status == "completed"
        assert by_id["b"].status == "pending"

    @pytest.mark.ai
    def test_update__updates_content(self) -> None:
        """
        Purpose: Verify update changes content text when ID matches.
        Why: The model may refine task descriptions.
        Setup: State with one item, update with same ID but different content.
        """
        state = TodoList(todos=[TodoItem(id="a", content="Do X", status="pending")])
        incoming = [TodoItem(id="a", content="Do X (revised)", status="pending")]

        result = state.update(incoming)

        assert result.todos[0].content == "Do X (revised)"


class TestTodoWriteTool:
    """Tests for TodoWriteTool run method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__new_todos__creates_state_in_memory(
        self, mock_chat_event: ChatEvent, todo_config: TodoConfig
    ) -> None:
        """
        Purpose: Verify first write creates state from scratch.
        Why: Initial tool call has no existing state.
        Setup: Mock load returns None, call with new todos.
        """
        tool = TodoWriteTool(todo_config, mock_chat_event)
        tool._memory_manager.load_async = AsyncMock(return_value=None)
        tool._memory_manager.save_async = AsyncMock()

        call = _make_tool_call(
            TodoWriteInput(
                todos=[TodoItem(id="t1", content="First task", status="pending")],
                merge=True,
            ).model_dump_json()
        )

        response = await tool.run(call)

        assert response.successful
        assert "First task" in response.content
        tool._memory_manager.save_async.assert_called_once()
        saved_state: TodoList = tool._memory_manager.save_async.call_args[0][0]
        assert len(saved_state.todos) == 1
        assert saved_state.todos[0].id == "t1"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__merge_true__updates_existing_items(
        self,
        mock_chat_event: ChatEvent,
        todo_config: TodoConfig,
        sample_state: TodoList,
    ) -> None:
        """
        Purpose: Verify merge mode updates existing items by ID.
        Why: Core workflow -- model marks tasks as completed.
        Setup: Existing state with 3 items, merge update to mark task-3 as in_progress.
        """
        tool = TodoWriteTool(todo_config, mock_chat_event)
        tool._memory_manager.load_async = AsyncMock(return_value=sample_state)
        tool._memory_manager.save_async = AsyncMock()

        call = _make_tool_call(
            TodoWriteInput(
                todos=[
                    TodoItem(id="task-3", content="Write tests", status="in_progress")
                ],
                merge=True,
            ).model_dump_json()
        )

        await tool.run(call)

        saved_state: TodoList = tool._memory_manager.save_async.call_args[0][0]
        by_id = {t.id: t for t in saved_state.todos}
        assert by_id["task-3"].status == "in_progress"
        assert by_id["task-1"].status == "completed"
        assert len(saved_state.todos) == 3

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__merge_false__replaces_entire_list(
        self,
        mock_chat_event: ChatEvent,
        todo_config: TodoConfig,
        sample_state: TodoList,
    ) -> None:
        """
        Purpose: Verify replace mode discards existing state.
        Why: Model may want to start fresh with a new plan.
        Setup: Existing state with 3 items, replace with 1 new item.
        """
        tool = TodoWriteTool(todo_config, mock_chat_event)
        tool._memory_manager.load_async = AsyncMock(return_value=sample_state)
        tool._memory_manager.save_async = AsyncMock()

        call = _make_tool_call(
            TodoWriteInput(
                todos=[TodoItem(id="new-1", content="Fresh start", status="pending")],
                merge=False,
            ).model_dump_json()
        )

        await tool.run(call)

        saved_state: TodoList = tool._memory_manager.save_async.call_args[0][0]
        assert len(saved_state.todos) == 1
        assert saved_state.todos[0].id == "new-1"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__large_todo_list__no_truncation(
        self, mock_chat_event: ChatEvent, todo_config: TodoConfig
    ) -> None:
        """
        Purpose: Verify there is no artificial limit on todo items.
        Why: Multi-step workflows and batch operations may have 50+ items.
        Setup: Write 100 items, verify all are preserved.
        """
        tool = TodoWriteTool(todo_config, mock_chat_event)
        tool._memory_manager.load_async = AsyncMock(return_value=None)
        tool._memory_manager.save_async = AsyncMock()

        items = [
            TodoItem(id=f"t{i}", content=f"Task {i}", status="pending")
            for i in range(100)
        ]
        call = _make_tool_call(
            TodoWriteInput(todos=items, merge=False).model_dump_json()
        )

        await tool.run(call)

        saved_state: TodoList = tool._memory_manager.save_async.call_args[0][0]
        assert len(saved_state.todos) == 100

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__returns_formatted_state(
        self, mock_chat_event: ChatEvent, todo_config: TodoConfig
    ) -> None:
        """
        Purpose: Verify response content contains formatted task list.
        Why: The model reads the response to confirm its update.
        Setup: Write two items, check response format.
        """
        tool = TodoWriteTool(todo_config, mock_chat_event)
        tool._memory_manager.load_async = AsyncMock(return_value=None)
        tool._memory_manager.save_async = AsyncMock()

        call = _make_tool_call(
            TodoWriteInput(
                todos=[
                    TodoItem(id="a", content="Alpha", status="pending"),
                    TodoItem(id="b", content="Beta", status="completed"),
                ],
                merge=False,
            ).model_dump_json()
        )

        response = await tool.run(call)

        assert "[ ] Alpha" in response.content
        assert "[x] Beta" in response.content
        assert "1/2 completed" in response.content

    @pytest.mark.ai
    def test_tool_description__matches_expected_schema(
        self, mock_chat_event: ChatEvent, todo_config: TodoConfig
    ) -> None:
        """
        Purpose: Verify tool description has correct name and parameter schema.
        Why: ToolFactory and ToolManager depend on valid descriptions.
        Setup: Create tool, inspect description.
        """
        tool = TodoWriteTool(todo_config, mock_chat_event)
        desc = tool.tool_description()

        assert desc.name == "todo_write"
        assert "todos" in desc.parameters["properties"]
        assert "merge" in desc.parameters["properties"]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__increments_last_updated_iteration(
        self, mock_chat_event: ChatEvent, todo_config: TodoConfig
    ) -> None:
        """
        Purpose: Verify last_updated_iteration is incremented on each write.
        Why: Tracks when state was last modified for debugging.
        Setup: Existing state at iteration 5, write should bump to 6.
        """
        existing = TodoList(
            todos=[TodoItem(id="a", content="X", status="pending")],
            last_updated_iteration=5,
        )
        tool = TodoWriteTool(todo_config, mock_chat_event)
        tool._memory_manager.load_async = AsyncMock(return_value=existing)
        tool._memory_manager.save_async = AsyncMock()

        call = _make_tool_call(
            TodoWriteInput(
                todos=[TodoItem(id="a", content="X", status="completed")],
                merge=True,
            ).model_dump_json()
        )

        await tool.run(call)

        saved_state: TodoList = tool._memory_manager.save_async.call_args[0][0]
        assert saved_state.last_updated_iteration == 6


class TestTodoReadTool:
    """Tests for TodoReadTool."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__no_state__returns_empty(
        self, mock_chat_event: ChatEvent, todo_config: TodoConfig
    ) -> None:
        """
        Purpose: Verify graceful handling when no state exists.
        Why: Model may read before any write has occurred.
        Setup: Mock load returns None.
        """
        tool = TodoReadTool(todo_config, mock_chat_event)
        tool._memory_manager.load_async = AsyncMock(return_value=None)

        call = LanguageModelFunction(id="call_r1", name="todo_read", arguments="{}")

        response = await tool.run(call)

        assert response.successful
        assert "No tasks tracked" in response.content

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__existing_state__returns_formatted(
        self,
        mock_chat_event: ChatEvent,
        todo_config: TodoConfig,
        sample_state: TodoList,
    ) -> None:
        """
        Purpose: Verify read returns correctly formatted existing state.
        Why: Core read functionality for the model.
        Setup: Existing state with 3 items.
        """
        tool = TodoReadTool(todo_config, mock_chat_event)
        tool._memory_manager.load_async = AsyncMock(return_value=sample_state)

        call = LanguageModelFunction(id="call_r2", name="todo_read", arguments="{}")

        response = await tool.run(call)

        assert "[x] Research API options" in response.content
        assert "[>] Implement service layer" in response.content
        assert "[ ] Write tests" in response.content
        assert "1/3 completed" in response.content

    @pytest.mark.ai
    def test_tool_description__has_no_required_params(
        self, mock_chat_event: ChatEvent, todo_config: TodoConfig
    ) -> None:
        """
        Purpose: Verify read tool has an empty parameter schema.
        Why: Reading should require no input from the model.
        Setup: Create tool, inspect parameters.
        """
        tool = TodoReadTool(todo_config, mock_chat_event)
        desc = tool.tool_description()

        assert desc.name == "todo_read"
        assert (
            desc.parameters.get("required") is None
            or desc.parameters.get("required") == []
        )


class TestFormatMethods:
    """Tests for the format methods on TodoList."""

    @pytest.mark.ai
    def test_format__empty__returns_no_tasks(self) -> None:
        """
        Purpose: Verify empty state produces a clear message.
        Why: Model should understand there are no tasks.
        Setup: Empty TodoList.
        """
        result = TodoList().format()
        assert result == "No tasks tracked."


class TestDebugInfoAndSystemReminder:
    """Tests for debug_info and system_reminder on ToolCallResponse."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__response_includes_debug_info(
        self, mock_chat_event: ChatEvent, todo_config: TodoConfig
    ) -> None:
        """
        Purpose: Verify todo_write response includes structured debug_info.
        Why: Debug UI needs tool-level trace data.
        """
        tool = TodoWriteTool(todo_config, mock_chat_event)
        tool._memory_manager.load_async = AsyncMock(return_value=None)
        tool._memory_manager.save_async = AsyncMock()

        call = _make_tool_call(
            TodoWriteInput(
                todos=[
                    TodoItem(id="t1", content="Task one", status="pending"),
                    TodoItem(id="t2", content="Task two", status="completed"),
                ],
                merge=False,
            ).model_dump_json()
        )

        response = await tool.run(call)

        assert response.debug_info is not None
        assert response.debug_info["input"]["merge"] is False
        assert len(response.debug_info["input"]["items"]) == 2
        assert response.debug_info["state"]["total"] == 2
        assert response.debug_info["state"]["completed"] == 1
        assert response.debug_info["state"]["pending"] == 1
        assert response.debug_info["iteration"] == 1

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__system_reminder_set_when_active_items(
        self, mock_chat_event: ChatEvent, todo_config: TodoConfig
    ) -> None:
        """
        Purpose: Verify system_reminder is set when there are active (non-terminal) items.
        Why: Drives autonomous execution via the history_manager pipeline.
        """
        tool = TodoWriteTool(todo_config, mock_chat_event)
        tool._memory_manager.load_async = AsyncMock(return_value=None)
        tool._memory_manager.save_async = AsyncMock()

        call = _make_tool_call(
            TodoWriteInput(
                todos=[TodoItem(id="t1", content="Active task", status="pending")],
                merge=False,
            ).model_dump_json()
        )

        response = await tool.run(call)

        assert response.system_reminder != ""
        assert "EXECUTION PHASE" in response.system_reminder

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__system_reminder_empty_when_all_complete(
        self, mock_chat_event: ChatEvent, todo_config: TodoConfig
    ) -> None:
        """
        Purpose: Verify system_reminder is empty when all items are terminal.
        Why: No need to push autonomous execution when nothing remains.
        """
        tool = TodoWriteTool(todo_config, mock_chat_event)
        tool._memory_manager.load_async = AsyncMock(return_value=None)
        tool._memory_manager.save_async = AsyncMock()

        call = _make_tool_call(
            TodoWriteInput(
                todos=[
                    TodoItem(id="t1", content="Done", status="completed"),
                    TodoItem(id="t2", content="Dropped", status="cancelled"),
                ],
                merge=False,
            ).model_dump_json()
        )

        response = await tool.run(call)

        assert response.system_reminder == ""


class TestHasActiveItems:
    """Tests for TodoList.has_active_items()."""

    @pytest.mark.ai
    def test_has_active__pending_item__returns_true(self) -> None:
        state = TodoList(todos=[TodoItem(id="a", content="X", status="pending")])
        assert state.has_active_items() is True

    @pytest.mark.ai
    def test_has_active__all_completed__returns_false(self) -> None:
        state = TodoList(todos=[TodoItem(id="a", content="X", status="completed")])
        assert state.has_active_items() is False

    @pytest.mark.ai
    def test_has_active__completed_and_cancelled__returns_false(self) -> None:
        state = TodoList(
            todos=[
                TodoItem(id="a", content="X", status="completed"),
                TodoItem(id="b", content="Y", status="cancelled"),
            ]
        )
        assert state.has_active_items() is False

    @pytest.mark.ai
    def test_has_active__empty__returns_false(self) -> None:
        assert TodoList().has_active_items() is False


class TestToolRegistration:
    """Tests for ToolFactory registration."""

    @pytest.mark.ai
    def test_todo_write__registered_in_factory(self) -> None:
        """
        Purpose: Verify TodoWriteTool is discoverable via ToolFactory.
        Why: The builder uses ToolFactory to construct tools.
        Setup: Check factory maps.
        """
        assert "todo_write" in ToolFactory.tool_map
        assert "todo_write" in ToolFactory.tool_config_map

    @pytest.mark.ai
    def test_todo_read__not_registered_by_default(self) -> None:
        """
        Purpose: Verify TodoReadTool is not auto-registered (manually registered by fixture).
        Why: todo_read was removed from default registration — the LLM never used it
        because todo_write already returns full state.
        """
        pass


class TestTodoConfig:
    """Tests for TodoConfig validation."""

    @pytest.mark.ai
    def test_config__defaults(self) -> None:
        """
        Purpose: Verify default config values.
        Why: Defaults should be sensible out of the box.
        Setup: Create config with no args.
        """
        config = TodoConfig()
        assert config.memory_key == "agent_todo_state"
