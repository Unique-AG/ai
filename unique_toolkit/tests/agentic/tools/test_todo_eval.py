"""Multi-step workflow evaluation tests for TODO task tracking.

These tests simulate realistic agentic conversation flows by driving
TodoWriteTool through a scripted sequence of tool calls and verifying
that state transitions, injection, and formatting behave correctly
across multiple iterations.

All tests are deterministic and CI-safe (no LLM or network calls).
"""

from __future__ import annotations

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
        ToolFactory.register_tool(TodoReadTool, TodoConfig)
    yield


@pytest.fixture
def mock_event() -> ChatEvent:
    event = Mock(spec=ChatEvent)
    event.user_id = "user_eval"
    event.company_id = "company_eval"
    event.chat_id = "chat_eval"
    event.assistant_id = "assistant_eval"
    mock_payload = Mock()
    mock_payload.chat_id = "chat_eval"
    mock_payload.assistant_message = Mock()
    mock_payload.assistant_message.id = "assist_msg_eval"
    event.payload = mock_payload
    return event


@pytest.fixture
def shared_memory() -> dict[str, TodoList | None]:
    """Simulates ShortTermMemory as a simple dict so writes persist across iterations."""
    return {"agent_todo_state": None}


def _build_tool(
    event: ChatEvent,
    shared_memory: dict[str, TodoList | None],
    config: TodoConfig | None = None,
) -> TodoWriteTool:
    """Build a TodoWriteTool wired to the shared in-memory store."""
    cfg = config or TodoConfig()
    tool = TodoWriteTool(cfg, event)
    tool._memory_manager.load_async = AsyncMock(
        side_effect=lambda: shared_memory.get(cfg.memory_key)
    )
    tool._memory_manager.save_async = AsyncMock(
        side_effect=lambda state: shared_memory.__setitem__(cfg.memory_key, state)
    )
    return tool


def _build_read_tool(
    event: ChatEvent,
    shared_memory: dict[str, TodoList | None],
    config: TodoConfig | None = None,
) -> TodoReadTool:
    cfg = config or TodoConfig()
    tool = TodoReadTool(cfg, event)
    tool._memory_manager.load_async = AsyncMock(
        side_effect=lambda: shared_memory.get(cfg.memory_key)
    )
    return tool


def _make_write_call(
    todos: list[TodoItem],
    merge: bool = True,
    call_id: str = "call_0",
) -> LanguageModelFunction:
    return LanguageModelFunction(
        id=call_id,
        name="todo_write",
        arguments=TodoWriteInput(todos=todos, merge=merge).model_dump_json(),
    )


class TestTodoMultiStepWorkflow:
    """Simulate a realistic 3-task research workflow across multiple iterations.

    Flow:
      Iteration 1: Model creates 3 pending tasks
      Iteration 2: Model marks task-1 as in_progress
      Iteration 3: Model completes task-1, starts task-2
      Iteration 4: Model completes task-2, starts task-3
      Iteration 5: Model completes task-3
    """

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_full_lifecycle__pending_through_completed(
        self, mock_event: ChatEvent, shared_memory: dict
    ) -> None:
        """
        Purpose: Verify a full 5-iteration lifecycle of 3 tasks.
        Why: The primary use case -- multi-step research with progressive updates.
        Setup: 5 sequential write calls simulating model behavior.
        """
        tool = _build_tool(mock_event, shared_memory)

        tasks = [
            TodoItem(id="research", content="Research API options", status="pending"),
            TodoItem(id="implement", content="Implement service", status="pending"),
            TodoItem(id="test", content="Write tests", status="pending"),
        ]
        await tool.run(_make_write_call(tasks, merge=False, call_id="iter1"))

        state = shared_memory["agent_todo_state"]
        assert state is not None
        assert len(state.todos) == 3
        assert all(t.status == "pending" for t in state.todos)

        await tool.run(
            _make_write_call(
                [
                    TodoItem(
                        id="research",
                        content="Research API options",
                        status="in_progress",
                    )
                ],
                call_id="iter2",
            )
        )
        state = shared_memory["agent_todo_state"]
        by_id = {t.id: t for t in state.todos}
        assert by_id["research"].status == "in_progress"
        assert by_id["implement"].status == "pending"

        await tool.run(
            _make_write_call(
                [
                    TodoItem(
                        id="research",
                        content="Research API options",
                        status="completed",
                    ),
                    TodoItem(
                        id="implement",
                        content="Implement service",
                        status="in_progress",
                    ),
                ],
                call_id="iter3",
            )
        )
        state = shared_memory["agent_todo_state"]
        by_id = {t.id: t for t in state.todos}
        assert by_id["research"].status == "completed"
        assert by_id["implement"].status == "in_progress"
        assert by_id["test"].status == "pending"

        await tool.run(
            _make_write_call(
                [
                    TodoItem(
                        id="implement", content="Implement service", status="completed"
                    ),
                    TodoItem(id="test", content="Write tests", status="in_progress"),
                ],
                call_id="iter4",
            )
        )

        response = await tool.run(
            _make_write_call(
                [TodoItem(id="test", content="Write tests", status="completed")],
                call_id="iter5",
            )
        )

        state = shared_memory["agent_todo_state"]
        assert all(t.status == "completed" for t in state.todos)
        assert state.last_updated_iteration == 5
        assert "3/3 completed" in response.content

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_system_reminder__reflects_active_state(
        self, mock_event: ChatEvent, shared_memory: dict
    ) -> None:
        """
        Purpose: Verify system_reminder on ToolCallResponse reflects active state.
        Why: The reminder drives autonomous execution via the history_manager pipeline.
        Setup: Write active items, check system_reminder is set; complete all, check it clears.
        """
        tool = _build_tool(mock_event, shared_memory)

        response = await tool.run(
            _make_write_call(
                [TodoItem(id="a", content="First task", status="pending")],
                merge=False,
                call_id="w1",
            )
        )

        assert response.system_reminder != ""
        assert "autonomously" in response.system_reminder

        response = await tool.run(
            _make_write_call(
                [TodoItem(id="a", content="First task", status="completed")],
                call_id="w2",
            )
        )

        assert response.system_reminder == ""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_mid_conversation_additions__merge_preserves_existing(
        self, mock_event: ChatEvent, shared_memory: dict
    ) -> None:
        """
        Purpose: Verify that adding new tasks mid-conversation preserves existing ones.
        Why: The model discovers new work and extends the plan without losing progress.
        Setup: Create 2 tasks, then merge 1 new task.
        """
        tool = _build_tool(mock_event, shared_memory)

        await tool.run(
            _make_write_call(
                [
                    TodoItem(id="a", content="Analyze data", status="completed"),
                    TodoItem(id="b", content="Build charts", status="in_progress"),
                ],
                merge=False,
                call_id="initial",
            )
        )

        await tool.run(
            _make_write_call(
                [
                    TodoItem(
                        id="c", content="Add regulatory risks section", status="pending"
                    )
                ],
                merge=True,
                call_id="addition",
            )
        )

        state = shared_memory["agent_todo_state"]
        assert len(state.todos) == 3
        by_id = {t.id: t for t in state.todos}
        assert by_id["a"].status == "completed"
        assert by_id["b"].status == "in_progress"
        assert by_id["c"].status == "pending"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_read_tool__returns_state_written_by_write_tool(
        self, mock_event: ChatEvent, shared_memory: dict
    ) -> None:
        """
        Purpose: Verify TodoReadTool sees state written by TodoWriteTool.
        Why: The model may read state between writes to confirm progress.
        Setup: Write 2 items, then read.
        """
        write_tool = _build_tool(mock_event, shared_memory)
        read_tool = _build_read_tool(mock_event, shared_memory)

        await write_tool.run(
            _make_write_call(
                [
                    TodoItem(id="x", content="Task X", status="pending"),
                    TodoItem(id="y", content="Task Y", status="completed"),
                ],
                merge=False,
                call_id="w1",
            )
        )

        read_call = LanguageModelFunction(id="r1", name="todo_read", arguments="{}")
        response = await read_tool.run(read_call)

        assert "Task X" in response.content
        assert "Task Y" in response.content
        assert "1/2 completed" in response.content


class TestTodoEdgeCases:
    """Edge cases and boundary conditions for multi-step flows."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_truncation__mid_workflow__keeps_earliest_items(
        self, mock_event: ChatEvent, shared_memory: dict
    ) -> None:
        """
        Purpose: Verify truncation at max_todos during an active workflow.
        Why: Guard rail must not crash or corrupt state when the model overshoots.
        Setup: Config max_todos=3, create 2 items, then merge 3 more (total 5 > 3).
        """
        config = TodoConfig(max_todos=3)
        tool = _build_tool(mock_event, shared_memory, config=config)

        await tool.run(
            _make_write_call(
                [
                    TodoItem(id="a", content="Task A", status="completed"),
                    TodoItem(id="b", content="Task B", status="in_progress"),
                ],
                merge=False,
                call_id="w1",
            )
        )

        await tool.run(
            _make_write_call(
                [
                    TodoItem(id="c", content="Task C", status="pending"),
                    TodoItem(id="d", content="Task D", status="pending"),
                    TodoItem(id="e", content="Task E", status="pending"),
                ],
                merge=True,
                call_id="w2",
            )
        )

        state = shared_memory["agent_todo_state"]
        assert len(state.todos) == 3

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_replace_then_merge__clean_slate(
        self, mock_event: ChatEvent, shared_memory: dict
    ) -> None:
        """
        Purpose: Verify a replace followed by a merge works on the new state.
        Why: Model may start over and then extend the fresh plan.
        Setup: Create initial state, replace entirely, then merge a new item.
        """
        tool = _build_tool(mock_event, shared_memory)

        await tool.run(
            _make_write_call(
                [TodoItem(id="old", content="Old plan", status="pending")],
                merge=False,
                call_id="w1",
            )
        )

        await tool.run(
            _make_write_call(
                [TodoItem(id="new-a", content="New plan A", status="pending")],
                merge=False,
                call_id="w2",
            )
        )

        state = shared_memory["agent_todo_state"]
        assert len(state.todos) == 1
        assert state.todos[0].id == "new-a"

        await tool.run(
            _make_write_call(
                [TodoItem(id="new-b", content="New plan B", status="pending")],
                merge=True,
                call_id="w3",
            )
        )

        state = shared_memory["agent_todo_state"]
        assert len(state.todos) == 2
        ids = {t.id for t in state.todos}
        assert ids == {"new-a", "new-b"}

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_all_completed__system_reminder_skips(
        self, mock_event: ChatEvent, shared_memory: dict
    ) -> None:
        """
        Purpose: Verify has_active_items() is false when all items are terminal.
        Why: The orchestrator skips injection when no actionable work remains.
        Setup: Mix of completed and cancelled tasks -- both are terminal.
        """
        tool = _build_tool(mock_event, shared_memory)

        await tool.run(
            _make_write_call(
                [
                    TodoItem(id="a", content="Task A", status="completed"),
                    TodoItem(id="b", content="Task B", status="cancelled"),
                    TodoItem(id="c", content="Task C", status="completed"),
                ],
                merge=False,
                call_id="w1",
            )
        )

        state = shared_memory["agent_todo_state"]
        assert not state.has_active_items()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_iteration_counter__increments_across_all_writes(
        self, mock_event: ChatEvent, shared_memory: dict
    ) -> None:
        """
        Purpose: Verify last_updated_iteration increments on every merge write.
        Why: Debugging and ordering of state changes.
        Setup: 4 sequential merge writes, verify counter is 4 at the end.
        """
        tool = _build_tool(mock_event, shared_memory)

        for i in range(4):
            await tool.run(
                _make_write_call(
                    [TodoItem(id=f"t{i}", content=f"Iteration {i}", status="pending")],
                    merge=True,
                    call_id=f"w{i}",
                )
            )

        state = shared_memory["agent_todo_state"]
        assert state is not None
        assert state.last_updated_iteration == 4

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_iteration_counter__preserved_on_replace(
        self, mock_event: ChatEvent, shared_memory: dict
    ) -> None:
        """
        Purpose: Verify replace (merge=False) preserves the iteration counter.
        Why: The counter tracks total writes, not just merges.
        Setup: 3 merge writes, then a replace, verify counter is 4 (not reset to 1).
        """
        tool = _build_tool(mock_event, shared_memory)

        for i in range(3):
            await tool.run(
                _make_write_call(
                    [TodoItem(id=f"t{i}", content=f"Step {i}", status="pending")],
                    merge=True,
                    call_id=f"w{i}",
                )
            )

        state = shared_memory["agent_todo_state"]
        assert state.last_updated_iteration == 3

        await tool.run(
            _make_write_call(
                [TodoItem(id="fresh", content="Fresh start", status="pending")],
                merge=False,
                call_id="w3",
            )
        )

        state = shared_memory["agent_todo_state"]
        assert len(state.todos) == 1
        assert state.todos[0].id == "fresh"
        assert state.last_updated_iteration == 4

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_cancelled_items__preserved_through_merges(
        self, mock_event: ChatEvent, shared_memory: dict
    ) -> None:
        """
        Purpose: Verify cancelled items survive merge operations.
        Why: Cancelled tasks should remain visible in the history.
        Setup: Create 2 tasks, cancel one, merge a new task, verify all 3 present.
        """
        tool = _build_tool(mock_event, shared_memory)

        await tool.run(
            _make_write_call(
                [
                    TodoItem(id="keep", content="Keep this", status="in_progress"),
                    TodoItem(id="drop", content="Drop this", status="pending"),
                ],
                merge=False,
                call_id="w1",
            )
        )

        await tool.run(
            _make_write_call(
                [TodoItem(id="drop", content="Drop this", status="cancelled")],
                merge=True,
                call_id="w2",
            )
        )

        await tool.run(
            _make_write_call(
                [TodoItem(id="new", content="New task", status="pending")],
                merge=True,
                call_id="w3",
            )
        )

        state = shared_memory["agent_todo_state"]
        assert len(state.todos) == 3
        by_id = {t.id: t for t in state.todos}
        assert by_id["drop"].status == "cancelled"
        assert by_id["keep"].status == "in_progress"
        assert by_id["new"].status == "pending"
