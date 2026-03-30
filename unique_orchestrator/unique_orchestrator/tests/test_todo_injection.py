"""Tests for TODO tool injection in the builder.

Tests focus on _inject_todo_tools adding todo_write to the space tools
when todo tracking is enabled, and TodoConfig defaults.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from unique_toolkit.agentic.tools.experimental.todo.config import TodoConfig

try:
    from unique_toolkit.agentic.tools.experimental.todo import (
        schemas as _todo_schemas,  # noqa: F401
    )

    _todo_available = True
except ImportError:
    _todo_available = False

pytestmark = pytest.mark.skipif(
    not _todo_available,
    reason="unique_toolkit.agentic.tools.experimental.todo not installed",
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
        mock_config.agent.experimental.todo_tracking = TodoConfig()
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
        mock_config.agent.experimental.todo_tracking = TodoConfig()
        mock_config.space.tools = []

        result = _inject_todo_tools(mock_config)

        tool_names = [t.name for t in result]
        assert "todo_read" not in tool_names

    @pytest.mark.ai
    def test_no_duplicate_when_already_present(self) -> None:
        """todo_write is not duplicated if already in space tools."""
        from unique_orchestrator.unique_ai_builder import _inject_todo_tools

        mock_config = MagicMock()
        mock_config.agent.experimental.todo_tracking = TodoConfig()
        existing_todo = MagicMock()
        existing_todo.name = "todo_write"
        mock_config.space.tools = [existing_todo]

        result = _inject_todo_tools(mock_config)

        todo_write_count = sum(1 for t in result if t.name == "todo_write")
        assert todo_write_count == 1

    @pytest.mark.ai
    def test_passes_config_directly_to_tool(self) -> None:
        """The TodoConfig instance is passed directly as tool configuration."""
        from unique_orchestrator.unique_ai_builder import _inject_todo_tools

        todo_cfg = TodoConfig(
            system_prompt="Custom system prompt",
            execution_reminder="Custom reminder",
        )
        mock_config = MagicMock()
        mock_config.agent.experimental.todo_tracking = todo_cfg
        mock_config.space.tools = []

        result = _inject_todo_tools(mock_config)

        todo_tool = [t for t in result if t.name == "todo_write"][0]
        assert todo_tool.configuration is todo_cfg
        assert todo_tool.configuration.system_prompt == "Custom system prompt"
        assert todo_tool.configuration.execution_reminder == "Custom reminder"


class TestTodoConfig:
    """Tests for TodoConfig defaults and overrides."""

    @pytest.mark.ai
    def test_defaults(self) -> None:
        config = TodoConfig()
        assert config.memory_key == "agent_todo_state"
        assert "todo_write" in config.system_prompt
        assert "EXECUTION PHASE" in config.execution_reminder

    @pytest.mark.ai
    def test_prompt_overrides(self) -> None:
        config = TodoConfig(
            system_prompt="Override system",
            execution_reminder="Override reminder",
        )
        assert config.system_prompt == "Override system"
        assert config.execution_reminder == "Override reminder"
