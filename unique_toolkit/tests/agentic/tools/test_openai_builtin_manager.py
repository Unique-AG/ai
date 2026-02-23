"""Tests for OpenAIBuiltInToolManager (build_manager, _build_tool, get_all_openai_builtin_tools)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unique_toolkit.agentic.tools.config import ToolBuildConfig
from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInTool,
    OpenAIBuiltInToolName,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.config import (
    CodeInterpreterExtendedConfig,
    OpenAICodeInterpreterConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.manager import OpenAIBuiltInToolManager


@pytest.mark.ai
@pytest.mark.asyncio
async def test_build_tool_code_interpreter_passes_tool_config_not_extended_config() -> (
    None
):
    """
    Purpose: Verify _build_tool passes configuration.tool_config (OpenAICodeInterpreterConfig)
    to OpenAICodeInterpreterTool.build_tool, not the full CodeInterpreterExtendedConfig.
    Why this matters: Fix for bug where manager expected OpenAICodeInterpreterConfig in
    ToolBuildConfig but tool config was refactored to CodeInterpreterExtendedConfig.
    """
    tool_config = ToolBuildConfig(
        name=OpenAIBuiltInToolName.CODE_INTERPRETER,
        configuration=CodeInterpreterExtendedConfig(
            tool_config=OpenAICodeInterpreterConfig(expires_after_minutes=30),
        ),
        is_enabled=True,
        is_exclusive=True,
    )
    mock_built_tool = MagicMock(spec=OpenAIBuiltInTool)
    build_tool_async = AsyncMock(return_value=mock_built_tool)

    with patch(
        "unique_toolkit.agentic.tools.openai_builtin.manager.OpenAICodeInterpreterTool",
        build_tool=build_tool_async,
    ):
        result = await OpenAIBuiltInToolManager._build_tool(
            uploaded_files=[],
            content_service=MagicMock(),
            user_id="user-1",
            company_id="company-1",
            chat_id="chat-1",
            client=MagicMock(),
            tool_config=tool_config,
        )

    assert result is mock_built_tool
    build_tool_async.assert_called_once()
    call_kwargs = build_tool_async.call_args.kwargs
    assert call_kwargs["config"] is tool_config.configuration.tool_config
    assert isinstance(call_kwargs["config"], OpenAICodeInterpreterConfig)
    assert call_kwargs["config"].expires_after_minutes == 30
    assert call_kwargs["is_exclusive"] is True


@pytest.mark.ai
@pytest.mark.asyncio
async def test_build_tool_unknown_name_raises() -> None:
    """Unknown built-in tool name raises ValueError (e.g. new enum value without branch in _build_tool)."""
    tool_config = MagicMock()
    tool_config.name = "unknown_builtin"
    tool_config.configuration = CodeInterpreterExtendedConfig()
    tool_config.is_exclusive = False

    with pytest.raises(ValueError, match="Unknown built-in tool name: unknown_builtin"):
        await OpenAIBuiltInToolManager._build_tool(
            uploaded_files=[],
            content_service=MagicMock(),
            user_id="user-1",
            company_id="company-1",
            chat_id="chat-1",
            client=MagicMock(),
            tool_config=tool_config,
        )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_build_manager_only_includes_enabled_builtin_tools() -> None:
    """build_manager only builds tools that are enabled and have name in OpenAIBuiltInToolName."""
    mock_tool = MagicMock(spec=OpenAIBuiltInTool)
    build_tool_async = AsyncMock(return_value=mock_tool)

    enabled_config = ToolBuildConfig(
        name=OpenAIBuiltInToolName.CODE_INTERPRETER,
        configuration=CodeInterpreterExtendedConfig(),
        is_enabled=True,
    )
    disabled_config = ToolBuildConfig(
        name=OpenAIBuiltInToolName.CODE_INTERPRETER,
        configuration=CodeInterpreterExtendedConfig(),
        is_enabled=False,
    )

    with patch(
        "unique_toolkit.agentic.tools.openai_builtin.manager.OpenAICodeInterpreterTool",
        build_tool=build_tool_async,
    ):
        manager = await OpenAIBuiltInToolManager.build_manager(
            uploaded_files=[],
            content_service=MagicMock(),
            user_id="user-1",
            company_id="company-1",
            chat_id="chat-1",
            client=MagicMock(),
            tool_configs=[enabled_config, disabled_config],
        )

    assert build_tool_async.call_count == 1
    tools = manager.get_all_openai_builtin_tools()
    assert len(tools) == 1
    assert tools[0] is mock_tool


@pytest.mark.ai
@pytest.mark.asyncio
async def test_build_manager_skips_non_builtin_tool_names() -> None:
    """build_manager skips tool configs whose name is not in OpenAIBuiltInToolName."""
    build_tool_async = AsyncMock()
    non_builtin_config = MagicMock()
    non_builtin_config.name = "some_other_tool"
    non_builtin_config.is_enabled = True

    with patch(
        "unique_toolkit.agentic.tools.openai_builtin.manager.OpenAICodeInterpreterTool",
        build_tool=build_tool_async,
    ):
        manager = await OpenAIBuiltInToolManager.build_manager(
            uploaded_files=[],
            content_service=MagicMock(),
            user_id="user-1",
            company_id="company-1",
            chat_id="chat-1",
            client=MagicMock(),
            tool_configs=[non_builtin_config],
        )

    build_tool_async.assert_not_called()
    assert len(manager.get_all_openai_builtin_tools()) == 0


@pytest.mark.ai
def test_get_all_openai_builtin_tools_returns_copy() -> None:
    """get_all_openai_builtin_tools returns a copy so caller cannot mutate internal list."""
    tool = MagicMock(spec=OpenAIBuiltInTool)
    manager = OpenAIBuiltInToolManager(builtin_tools=[tool])

    first = manager.get_all_openai_builtin_tools()
    second = manager.get_all_openai_builtin_tools()

    assert first == second
    assert first is not second
    first.clear()
    assert len(manager.get_all_openai_builtin_tools()) == 1
