from unittest.mock import AsyncMock, MagicMock

import pytest
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

from unique_orchestrator.unique_ai import UniqueAI


def _make_loop_response(usage: LanguageModelTokenUsage | None) -> MagicMock:
    response = MagicMock()
    response.tool_calls = None
    response.message = MagicMock()
    response.message.references = []
    response.message.text = "response text"
    response.is_empty.return_value = False
    response.usage = usage
    return response


def _build_run_ua(loop_responses: list[MagicMock], max_iterations: int):
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
    mock_tool_manager.filter_duplicate_tool_calls.side_effect = lambda x: x
    mock_tool_manager.filter_tool_calls_by_max_tool_calls_allowed.side_effect = (
        lambda x: x
    )
    mock_tool_manager.does_a_tool_take_control.return_value = False
    mock_tool_manager.should_stop_after_tool_calls.return_value = False
    mock_tool_manager.get_evaluation_check_list.return_value = []

    mock_debug_info_manager = MagicMock()
    mock_debug_info_manager.get.return_value = {"tools": []}

    mock_config = MagicMock()
    mock_config.effective_max_loop_iterations = max_iterations
    mock_config.agent.prompt_config.user_metadata = []

    mock_history_manager = MagicMock()
    mock_history_manager.get_history_for_model_call = AsyncMock(
        return_value=MagicMock()
    )
    mock_history_manager._append_tool_calls_to_history = MagicMock()
    mock_history_manager.add_tool_call_results = MagicMock()
    mock_history_manager.extract_message_tools.return_value = []

    mock_postprocessor_manager = MagicMock()
    mock_postprocessor_manager.run_postprocessors = AsyncMock(return_value=None)
    mock_postprocessor_manager.get_execution_times.return_value = {}
    mock_postprocessor_manager.get_usage.return_value = None

    mock_evaluation_manager = MagicMock()
    mock_evaluation_manager.run_evaluations = AsyncMock(return_value=[])
    mock_evaluation_manager.get_execution_times.return_value = {}
    mock_evaluation_manager.get_usage.return_value = None

    dummy_event = MagicMock()
    dummy_event.payload.assistant_message.id = "assist_1"
    dummy_event.payload.user_message.text = "query"
    dummy_event.payload.assistant_id = "assistant_123"
    dummy_event.payload.name = "TestAssistant"
    dummy_event.payload.user_metadata = {}
    dummy_event.payload.tool_parameters = {}
    dummy_event.company_id = "company_1"

    ua = UniqueAI(
        logger=MagicMock(),
        event=dummy_event,
        config=mock_config,
        chat_service=mock_chat_service,
        content_service=MagicMock(),
        debug_info_manager=mock_debug_info_manager,
        streaming_handler=MagicMock(),
        reference_manager=MagicMock(),
        thinking_manager=MagicMock(),
        tool_manager=mock_tool_manager,
        history_manager=mock_history_manager,
        evaluation_manager=mock_evaluation_manager,
        postprocessor_manager=mock_postprocessor_manager,
        message_step_logger=MagicMock(),
        mcp_servers=[],
        loop_iteration_runner=AsyncMock(side_effect=loop_responses),
    )
    ua._render_user_prompt = AsyncMock(return_value="user")  # type: ignore[method-assign]
    ua._render_system_prompt = AsyncMock(return_value="system")  # type: ignore[method-assign]
    ua._thinking_manager.thinking_is_displayed = MagicMock(return_value=True)
    ua._thinking_manager.update_start_text = MagicMock(return_value="")
    return ua


class TestAccumulateUsage:
    def test_accumulate_usage__none__is_noop(self):
        ua = _build_run_ua([_make_loop_response(None)], max_iterations=1)
        ua._accumulate_usage(None)
        assert ua._total_usage is None

    def test_accumulate_usage__single_call__sets_total(self):
        ua = _build_run_ua([_make_loop_response(None)], max_iterations=1)
        ua._accumulate_usage(
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            )
        )
        assert ua._total_usage == LanguageModelTokenUsage(
            completion_tokens=10, prompt_tokens=20, total_tokens=30
        )

    def test_accumulate_usage__multiple_calls__sums(self):
        ua = _build_run_ua([_make_loop_response(None)], max_iterations=1)
        ua._accumulate_usage(
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            )
        )
        ua._accumulate_usage(
            LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=2, total_tokens=3
            )
        )
        assert ua._total_usage == LanguageModelTokenUsage(
            completion_tokens=11, prompt_tokens=22, total_tokens=33
        )

    def test_accumulate_usage__none_mixed_with_real__ignores_none(self):
        ua = _build_run_ua([_make_loop_response(None)], max_iterations=1)
        ua._accumulate_usage(
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            )
        )
        ua._accumulate_usage(None)
        assert ua._total_usage == LanguageModelTokenUsage(
            completion_tokens=10, prompt_tokens=20, total_tokens=30
        )


class TestRunTokenUsageIntegration:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__debug_info_manager__receives_token_usage_key(self):
        """A single-iteration run with real usage on the loop response must
        surface it under debug_info's 'token_usage' key."""
        loop_response = _make_loop_response(
            LanguageModelTokenUsage(
                completion_tokens=12, prompt_tokens=34, total_tokens=46
            )
        )
        ua = _build_run_ua([loop_response], max_iterations=1)

        await ua.run()

        calls_by_key = {
            args[0][0]: args[0][1] for args in ua._debug_info_manager.add.call_args_list
        }
        assert "token_usage" in calls_by_key
        assert calls_by_key["token_usage"] == {
            "completionTokens": 12,
            "promptTokens": 34,
            "totalTokens": 46,
        }

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__no_usage_on_any_response__token_usage_is_none(self):
        """When usage is never populated (e.g. no supporting provider),
        the 'token_usage' key must be explicitly None, not absent/silent."""
        ua = _build_run_ua([_make_loop_response(None)], max_iterations=1)

        await ua.run()

        calls_by_key = {
            args[0][0]: args[0][1] for args in ua._debug_info_manager.add.call_args_list
        }
        assert "token_usage" in calls_by_key
        assert calls_by_key["token_usage"] is None

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__postprocessor_usage__added_to_loop_usage(self):
        """FollowUpPostprocessor (and any postprocessor) makes its own LLM
        call outside _plan_or_execute() — its usage must be added to the
        same total, not silently dropped."""
        loop_response = _make_loop_response(
            LanguageModelTokenUsage(
                completion_tokens=12, prompt_tokens=34, total_tokens=46
            )
        )
        ua = _build_run_ua([loop_response], max_iterations=1)
        ua._postprocessor_manager.get_usage.return_value = LanguageModelTokenUsage(
            completion_tokens=3, prompt_tokens=7, total_tokens=10
        )

        await ua.run()

        calls_by_key = {
            args[0][0]: args[0][1] for args in ua._debug_info_manager.add.call_args_list
        }
        assert calls_by_key["token_usage"] == {
            "completionTokens": 15,
            "promptTokens": 41,
            "totalTokens": 56,
        }

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__reset_between_runs__does_not_leak_across_calls(self):
        """_total_usage must reset at the start of run(), so a second run()
        on the same UniqueAI instance doesn't inherit the prior run's total."""
        loop_response = _make_loop_response(
            LanguageModelTokenUsage(
                completion_tokens=5, prompt_tokens=5, total_tokens=10
            )
        )
        ua = _build_run_ua([loop_response, loop_response], max_iterations=1)

        await ua.run()
        await ua.run()

        calls_by_key = {
            args[0][0]: args[0][1] for args in ua._debug_info_manager.add.call_args_list
        }
        assert calls_by_key["token_usage"] == {
            "completionTokens": 5,
            "promptTokens": 5,
            "totalTokens": 10,
        }
