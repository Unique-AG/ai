"""Tests for UniqueAI._plan_or_execute forwarding Responses API `include` params."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from unique_toolkit.agentic.tools.tool_manager import ResponsesApiToolManager

from unique_orchestrator.unique_ai import UniqueAI


def _responses_api_tool_manager_stub(
    *,
    include_params: list[str],
) -> ResponsesApiToolManager:
    """Bare instance that passes isinstance(..., ResponsesApiToolManager) without __init__."""
    mgr = ResponsesApiToolManager.__new__(ResponsesApiToolManager)
    mgr.get_tool_definitions = MagicMock(return_value=[])
    mgr.get_forced_tools = MagicMock(return_value=[])
    mgr.get_required_include_params = MagicMock(return_value=include_params)
    return mgr


def _minimal_unique_ai(
    *,
    tool_manager: MagicMock | ResponsesApiToolManager,
    loop_iteration_runner: AsyncMock,
) -> UniqueAI:
    dummy_event = MagicMock()
    dummy_event.payload.assistant_message.id = "assist_1"
    dummy_event.payload.user_message.text = "query"
    dummy_event.payload.assistant_id = "assistant_123"
    dummy_event.payload.name = "TestAssistant"
    dummy_event.payload.user_metadata = {"key": "value"}
    dummy_event.payload.tool_parameters = {"param": "value"}
    dummy_event.payload.tool_choices = []
    dummy_event.payload.disabled_tools = []

    mock_config = MagicMock()
    mock_config.space.language_model = MagicMock()
    mock_config.agent.experimental.temperature = 0.7
    mock_config.agent.experimental.additional_llm_options = {}

    mock_chat_service = MagicMock()
    mock_reference_manager = MagicMock()
    mock_reference_manager.get_chunks.return_value = []

    return UniqueAI(
        logger=MagicMock(),
        event=dummy_event,
        config=mock_config,
        chat_service=mock_chat_service,
        content_service=MagicMock(),
        debug_info_manager=MagicMock(),
        streaming_handler=MagicMock(),
        reference_manager=mock_reference_manager,
        thinking_manager=MagicMock(),
        tool_manager=tool_manager,
        history_manager=MagicMock(),
        evaluation_manager=MagicMock(),
        postprocessor_manager=MagicMock(),
        message_step_logger=MagicMock(),
        mcp_servers=[],
        loop_iteration_runner=loop_iteration_runner,
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_plan_or_execute__sets_include_on_runner__when_responses_manager_returns_params() -> (
    None
):
    """
    Purpose: Verify kwargs passed to loop_iteration_runner include `include` when
    the tool manager is ResponsesApiToolManager and get_required_include_params is non-empty.
    Why this matters: UN-17972 requires `code_interpreter_call.outputs` on the Responses API.
    """
    loop_runner = AsyncMock(return_value=MagicMock())
    tool_mgr = _responses_api_tool_manager_stub(
        include_params=["code_interpreter_call.outputs"],
    )
    ua = _minimal_unique_ai(
        tool_manager=tool_mgr,
        loop_iteration_runner=loop_runner,
    )
    ua._compose_message_plan_execution = AsyncMock(return_value=[])

    await ua._plan_or_execute()

    loop_runner.assert_awaited_once()
    call_kw = loop_runner.await_args.kwargs
    assert call_kw["include"] == ["code_interpreter_call.outputs"]
    tool_mgr.get_required_include_params.assert_called_once_with()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_plan_or_execute__omits_include__when_responses_manager_returns_empty_list() -> (
    None
):
    """Purpose: When no built-in requests includes, the key must not be set."""
    loop_runner = AsyncMock(return_value=MagicMock())
    tool_mgr = _responses_api_tool_manager_stub(include_params=[])
    ua = _minimal_unique_ai(
        tool_manager=tool_mgr,
        loop_iteration_runner=loop_runner,
    )
    ua._compose_message_plan_execution = AsyncMock(return_value=[])

    await ua._plan_or_execute()

    assert "include" not in loop_runner.await_args.kwargs


@pytest.mark.ai
@pytest.mark.asyncio
async def test_plan_or_execute__omits_include__when_tool_manager_is_completions() -> (
    None
):
    """Purpose: Completions ToolManager must not receive Responses-only `include`."""
    loop_runner = AsyncMock(return_value=MagicMock())
    tool_mgr = MagicMock()
    tool_mgr.get_tool_definitions = MagicMock(return_value=[])
    tool_mgr.get_forced_tools = MagicMock(return_value=[])
    ua = _minimal_unique_ai(
        tool_manager=tool_mgr,
        loop_iteration_runner=loop_runner,
    )
    ua._compose_message_plan_execution = AsyncMock(return_value=[])

    await ua._plan_or_execute()

    assert "include" not in loop_runner.await_args.kwargs
