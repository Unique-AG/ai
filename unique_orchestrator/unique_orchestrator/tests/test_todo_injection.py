"""Tests for TODO tool injection in the builder.

Tests focus on _inject_todo_tools adding todo_write to the space tools
when todo tracking is enabled, and TodoTrackingConfig field parity with
the toolkit's TodoConfig.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unique_orchestrator.config import TodoTrackingConfig

try:
    from unique_toolkit.agentic.tools.todo import schemas as _todo_schemas  # noqa: F401

    _todo_available = True
except ImportError:
    _todo_available = False

pytestmark = pytest.mark.skipif(
    not _todo_available,
    reason="unique_toolkit.agentic.tools.todo not installed",
)


class TestInjectTodoTools:
    """Tests for _inject_todo_tools in the builder."""

    @pytest.mark.ai
    def test_returns_original_tools_when_tracking_disabled(self) -> None:
        """No tools added when todo_tracking is None."""
        from unique_orchestrator.unique_ai_builder import _inject_todo_tools

        mock_config = MagicMock()
        mock_config.agent.experimental.todo_tracking = None
        mock_config.space.tools = [MagicMock(name="search")]

        result = _inject_todo_tools(mock_config)

        assert result is mock_config.space.tools

    @pytest.mark.ai
    def test_adds_todo_write_when_tracking_enabled(self) -> None:
        """todo_write is added when todo_tracking is configured."""
        from unique_orchestrator.unique_ai_builder import _inject_todo_tools

        mock_config = MagicMock()
        mock_config.agent.experimental.todo_tracking = TodoTrackingConfig()
        existing_tool = MagicMock()
        existing_tool.name = "search"
        mock_config.space.tools = [existing_tool]

        result = _inject_todo_tools(mock_config)

        tool_names = [t.name for t in result]
        assert "todo_write" in tool_names

    @pytest.mark.ai
    def test_does_not_add_todo_read(self) -> None:
        """todo_read is not auto-registered."""
        from unique_orchestrator.unique_ai_builder import _inject_todo_tools

        mock_config = MagicMock()
        mock_config.agent.experimental.todo_tracking = TodoTrackingConfig()
        mock_config.space.tools = []

        result = _inject_todo_tools(mock_config)

        tool_names = [t.name for t in result]
        assert "todo_read" not in tool_names

    @pytest.mark.ai
    def test_no_duplicate_when_already_present(self) -> None:
        """todo_write is not duplicated if already in space tools."""
        from unique_orchestrator.unique_ai_builder import _inject_todo_tools

        mock_config = MagicMock()
        mock_config.agent.experimental.todo_tracking = TodoTrackingConfig()
        existing_todo = MagicMock()
        existing_todo.name = "todo_write"
        mock_config.space.tools = [existing_todo]

        result = _inject_todo_tools(mock_config)

        todo_write_count = sum(1 for t in result if t.name == "todo_write")
        assert todo_write_count == 1

    @pytest.mark.ai
    def test_passes_config_overrides_to_tool(self) -> None:
        """Prompt overrides from TodoTrackingConfig are passed through."""
        from unique_orchestrator.unique_ai_builder import _inject_todo_tools

        mock_config = MagicMock()
        mock_config.agent.experimental.todo_tracking = TodoTrackingConfig(
            system_prompt="Custom system prompt",
            execution_reminder="Custom reminder",
        )
        mock_config.space.tools = []

        result = _inject_todo_tools(mock_config)

        todo_tool = [t for t in result if t.name == "todo_write"][0]
        assert todo_tool.configuration.system_prompt == "Custom system prompt"
        assert todo_tool.configuration.execution_reminder == "Custom reminder"


class TestTodoTrackingConfig:
    """Tests for TodoTrackingConfig in orchestrator config."""

    @pytest.mark.ai
    def test_defaults(self) -> None:
        config = TodoTrackingConfig()
        assert config.memory_key == "agent_todo_state"
        assert config.system_prompt is None
        assert config.execution_reminder is None

    @pytest.mark.ai
    def test_field_parity_with_toolkit_config(self) -> None:
        """TodoTrackingConfig fields must be a superset of TodoConfig fields.

        Catches drift when someone adds a field to one but not the other.
        """
        from unique_toolkit.agentic.tools.todo.config import TodoConfig

        toolkit_fields = set(TodoConfig.model_fields.keys())
        orch_fields = set(TodoTrackingConfig.model_fields.keys())

        missing = toolkit_fields - orch_fields
        assert not missing, (
            f"TodoTrackingConfig is missing fields from TodoConfig: {missing}. "
            "Add them to prevent silent config drift."
        )

    @pytest.mark.ai
    def test_prompt_overrides(self) -> None:
        config = TodoTrackingConfig(
            system_prompt="Override system",
            execution_reminder="Override reminder",
        )
        assert config.system_prompt == "Override system"
        assert config.execution_reminder == "Override reminder"
