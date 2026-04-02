"""Tests for experimental tool injection in the builder.

Tests focus on _inject_experimental_tools discovering and appending
tools from ExperimentalConfig fields that declare _tool_name,
_tool_module, and enabled=True.
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


def _make_config(
    todo_tracking: TodoConfig | None = None,
) -> MagicMock:
    """Build a mock UniqueAIConfig with a real ExperimentalConfig."""
    from unique_orchestrator.config import ExperimentalConfig

    experimental = ExperimentalConfig(
        todo_tracking=todo_tracking or TodoConfig(),
    )

    mock_config = MagicMock()
    mock_config.agent.experimental = experimental
    mock_config.space.tools = []
    return mock_config


class TestInjectExperimentalTools:
    """Tests for _inject_experimental_tools in the builder."""

    @pytest.mark.ai
    def test_returns_original_tools_when_tracking_disabled(self) -> None:
        """No tools added when todo_tracking.enabled is False (default)."""
        from unique_orchestrator.unique_ai_builder import _inject_experimental_tools

        config = _make_config()
        config.space.tools = [MagicMock(name="search")]

        result = _inject_experimental_tools(config)

        assert result is config.space.tools

    @pytest.mark.ai
    def test_adds_todo_write_when_tracking_enabled(self) -> None:
        from unique_orchestrator.unique_ai_builder import _inject_experimental_tools

        config = _make_config(TodoConfig(enabled=True))
        existing_tool = MagicMock()
        existing_tool.name = "search"
        config.space.tools = [existing_tool]

        result = _inject_experimental_tools(config)

        tool_names = [t.name for t in result]
        assert "todo_write" in tool_names

    @pytest.mark.ai
    def test_does_not_add_todo_read(self) -> None:
        from unique_orchestrator.unique_ai_builder import _inject_experimental_tools

        config = _make_config(TodoConfig(enabled=True))

        result = _inject_experimental_tools(config)

        tool_names = [t.name for t in result]
        assert "todo_read" not in tool_names

    @pytest.mark.ai
    def test_no_duplicate_when_already_present(self) -> None:
        from unique_orchestrator.unique_ai_builder import _inject_experimental_tools

        config = _make_config(TodoConfig(enabled=True))
        existing_todo = MagicMock()
        existing_todo.name = "todo_write"
        config.space.tools = [existing_todo]

        result = _inject_experimental_tools(config)

        todo_write_count = sum(1 for t in result if t.name == "todo_write")
        assert todo_write_count == 1

    @pytest.mark.ai
    def test_passes_config_directly_to_tool(self) -> None:
        from unique_orchestrator.unique_ai_builder import _inject_experimental_tools

        todo_cfg = TodoConfig(
            enabled=True,
            system_prompt="Custom system prompt",
            execution_reminder="Custom reminder",
        )
        config = _make_config(todo_cfg)

        result = _inject_experimental_tools(config)

        todo_tool = [t for t in result if t.name == "todo_write"][0]
        assert todo_tool.configuration is todo_cfg
        assert todo_tool.configuration.system_prompt == "Custom system prompt"
        assert todo_tool.configuration.execution_reminder == "Custom reminder"

    @pytest.mark.ai
    def test_skips_fields_without_tool_metadata(self) -> None:
        """Fields like temperature, loop_configuration are ignored."""
        from unique_orchestrator.unique_ai_builder import _inject_experimental_tools

        config = _make_config(TodoConfig())

        result = _inject_experimental_tools(config)

        assert result is config.space.tools

    @pytest.mark.ai
    def test_discovers_tool_via_classvar(self) -> None:
        """Verifies dynamic discovery uses _tool_name and _tool_module."""
        assert hasattr(TodoConfig, "_tool_name")
        assert hasattr(TodoConfig, "_tool_module")
        assert TodoConfig._tool_name == "todo_write"


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
