"""Tests for TODO tool injection in the builder.

With the move to system_reminder on ToolCallResponse (instead of orchestrator-level
injection), these tests focus on _inject_todo_tools adding todo_write to the
space tools when todo tracking is enabled.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unique_orchestrator.config import TodoTrackingConfig

try:
    from unique_toolkit.agentic.tools.todo import schemas as _todo_schemas  # noqa: F401

    HAS_TODO_MODULE = True
except ImportError:
    HAS_TODO_MODULE = False

requires_todo = pytest.mark.skipif(
    not HAS_TODO_MODULE,
    reason="unique_toolkit.agentic.tools.todo not installed (needs toolkit >= 1.53.0)",
)


class TestInjectTodoTools:
    """Tests for _inject_todo_tools in the builder."""

    @pytest.mark.ai
    def test_returns_original_tools_when_tracking_disabled(self) -> None:
        """
        Purpose: Verify no tools added when todo_tracking is None.
        Why: Default config has no todo tracking.
        """
        from unique_orchestrator.unique_ai_builder import _inject_todo_tools

        mock_config = MagicMock()
        mock_config.agent.experimental.todo_tracking = None
        mock_config.space.tools = [MagicMock(name="search")]

        result = _inject_todo_tools(mock_config)

        assert result is mock_config.space.tools

    @requires_todo
    @pytest.mark.ai
    def test_adds_todo_write_when_tracking_enabled(self) -> None:
        """
        Purpose: Verify todo_write is added when todo_tracking is configured.
        Why: The tool must be available for the model to use.
        """
        from unique_orchestrator.unique_ai_builder import _inject_todo_tools

        mock_config = MagicMock()
        mock_config.agent.experimental.todo_tracking = TodoTrackingConfig()
        existing_tool = MagicMock()
        existing_tool.name = "search"
        mock_config.space.tools = [existing_tool]

        result = _inject_todo_tools(mock_config)

        tool_names = [t.name for t in result]
        assert "todo_write" in tool_names
        assert "search" in tool_names

    @requires_todo
    @pytest.mark.ai
    def test_does_not_add_todo_read(self) -> None:
        """
        Purpose: Verify todo_read is NOT added.
        Why: todo_read was removed — the LLM never used it because todo_write
        already returns full state in its response content.
        """
        from unique_orchestrator.unique_ai_builder import _inject_todo_tools

        mock_config = MagicMock()
        mock_config.agent.experimental.todo_tracking = TodoTrackingConfig()
        mock_config.space.tools = []

        result = _inject_todo_tools(mock_config)

        tool_names = [t.name for t in result]
        assert "todo_read" not in tool_names

    @requires_todo
    @pytest.mark.ai
    def test_skips_duplicate_if_already_present(self) -> None:
        """
        Purpose: Verify todo_write is not duplicated if already in space tools.
        Why: Prevents double-registration.
        """
        from unique_orchestrator.unique_ai_builder import _inject_todo_tools

        mock_config = MagicMock()
        mock_config.agent.experimental.todo_tracking = TodoTrackingConfig()
        existing_todo = MagicMock()
        existing_todo.name = "todo_write"
        mock_config.space.tools = [existing_todo]

        result = _inject_todo_tools(mock_config)

        todo_write_count = sum(1 for t in result if t.name == "todo_write")
        assert todo_write_count == 1


class TestTodoTrackingConfig:
    """Tests for TodoTrackingConfig in orchestrator config."""

    @pytest.mark.ai
    def test_defaults(self) -> None:
        config = TodoTrackingConfig()
        assert config.memory_key == "agent_todo_state"
        assert config.max_todos == 20

    @pytest.mark.ai
    def test_no_inject_system_reminder_field(self) -> None:
        """
        Purpose: Verify inject_system_reminder is no longer a config field.
        Why: Reminder injection moved to ToolCallResponse.system_reminder.
        """
        config = TodoTrackingConfig()
        assert (
            not hasattr(config, "inject_system_reminder")
            or "inject_system_reminder" not in config.model_fields
        )

    @pytest.mark.ai
    def test_no_system_reminder_location_field(self) -> None:
        """
        Purpose: Verify system_reminder_location is no longer a config field.
        Why: Reminder injection moved to ToolCallResponse.system_reminder.
        """
        config = TodoTrackingConfig()
        assert "system_reminder_location" not in config.model_fields
