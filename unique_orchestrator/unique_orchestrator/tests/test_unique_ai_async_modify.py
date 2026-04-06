"""Tests for async modify_assistant_message calls in UniqueAI.run() and _process_plan()."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unique_orchestrator.unique_ai import UniqueAI


def _make_ua(monkeypatch, *, feature_flag_enabled: bool = False):
    mock_feature_flags = MagicMock()
    mock_feature_flags.enable_new_answers_ui_un_14411.is_enabled.return_value = (
        feature_flag_enabled
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai.feature_flags", mock_feature_flags
    )

    mock_cancellation = MagicMock()
    mock_cancellation.is_cancelled = False
    mock_cancellation.on_cancellation.subscribe = MagicMock(return_value=MagicMock())
    mock_cancellation.check_cancellation_async = AsyncMock(return_value=False)

    mock_chat_service = MagicMock()
    mock_chat_service.cancellation = mock_cancellation
    mock_chat_service.get_debug_info_async = AsyncMock(return_value={})
    mock_chat_service.update_debug_info_async = AsyncMock(return_value=None)
    mock_chat_service.modify_assistant_message_async = AsyncMock(return_value=None)
    mock_chat_service.create_assistant_message_async = AsyncMock(
        return_value=MagicMock(id="assist_new")
    )

    mock_tool_manager = MagicMock()
    mock_tool_manager.available_tools = []
    mock_tool_manager.get_forced_tools.return_value = []
    mock_tool_manager.get_tool_definitions.return_value = []
    mock_tool_manager.get_evaluation_check_list.return_value = []

    mock_debug_info_manager = MagicMock()
    mock_debug_info_manager.get.return_value = {"tools": []}

    mock_config = MagicMock()
    mock_config.effective_max_loop_iterations = 1
    mock_config.agent.prompt_config.user_metadata = []
    mock_config.agent.experimental.open_file_tool_config.enabled = False
    mock_config.agent.input_token_distribution.enable_tool_call_persistence = False

    mock_history_manager = MagicMock()
    mock_history_manager.get_history_for_model_call = AsyncMock(
        return_value=MagicMock()
    )

    mock_postprocessor_manager = MagicMock()
    mock_postprocessor_manager.run_postprocessors = AsyncMock(return_value=None)
    mock_postprocessor_manager.get_execution_times.return_value = {}

    mock_evaluation_manager = MagicMock()
    mock_evaluation_manager.run_evaluations = AsyncMock(return_value=[])
    mock_evaluation_manager.get_execution_times.return_value = {}

    dummy_event = MagicMock()
    dummy_event.payload.assistant_message.id = "assist_1"
    dummy_event.payload.user_message.text = "query"
    dummy_event.payload.assistant_id = "assistant_123"
    dummy_event.payload.name = "TestAssistant"
    dummy_event.payload.user_metadata = {}
    dummy_event.payload.tool_parameters = {}
    dummy_event.company_id = "company_1"

    ua = UniqueAI.__new__(UniqueAI)
    ua._event = dummy_event
    ua._chat_service = mock_chat_service
    ua._tool_manager = mock_tool_manager
    ua._debug_info_manager = mock_debug_info_manager
    ua._config = mock_config
    ua._history_manager = mock_history_manager
    ua._postprocessor_manager = mock_postprocessor_manager
    ua._evaluation_manager = mock_evaluation_manager
    ua._reference_manager = MagicMock()
    ua._thinking_manager = MagicMock()
    ua._tool_took_control = False
    ua._latest_assistant_id = "assistant_123"
    ua._logger = MagicMock()
    ua.start_text = ""
    ua._mcp_servers = []
    ua._execution_times = []
    ua._current_loop_timing = {}
    ua.current_iteration_index = 0

    return ua


@pytest.mark.ai
@pytest.mark.asyncio
async def test_run_calls_modify_async_when_feature_flag_disabled(monkeypatch):
    """Line 198: modify_assistant_message_async is called when new answers UI is disabled."""
    ua = _make_ua(monkeypatch, feature_flag_enabled=False)

    empty_response = MagicMock()
    empty_response.message.original_text = None
    empty_response.message.text = ""
    empty_response.message.references = []
    empty_response.tool_calls = None
    empty_response.is_empty.return_value = True

    ua._plan_or_execute = AsyncMock(return_value=empty_response)

    await ua.run()

    ua._chat_service.modify_assistant_message_async.assert_any_call(
        content="Starting agentic loop..."
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_process_plan_calls_modify_async_on_empty_response(monkeypatch):
    """Line 361: modify_assistant_message_async is called with EMPTY_MESSAGE_WARNING."""
    ua = _make_ua(monkeypatch)

    empty_response = MagicMock()
    empty_response.is_empty.return_value = True

    result = await ua._process_plan(empty_response)

    assert result is True
    ua._chat_service.modify_assistant_message_async.assert_called()
