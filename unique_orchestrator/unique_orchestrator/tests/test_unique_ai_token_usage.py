from unittest.mock import AsyncMock, MagicMock

import pytest
from unique_toolkit.agentic.loop_runner import SupportsInvocationStats
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.language_model.invocation_stats import LanguageModelInvocationStats
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

from unique_orchestrator.unique_ai import UniqueAI

MODEL_NAME = "gpt-4"


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
    mock_config.space.language_model.name = MODEL_NAME

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
    mock_postprocessor_manager.get_invocation_stats.return_value = []

    mock_evaluation_manager = MagicMock()
    mock_evaluation_manager.run_evaluations = AsyncMock(return_value=[])
    mock_evaluation_manager.get_execution_times.return_value = {}
    mock_evaluation_manager.get_invocation_stats.return_value = []

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
    """Tests for how UniqueAI._invocation_stats is populated from the main loop."""

    def test_main_loop__none_usage__is_noop(self):
        ua = _build_run_ua([_make_loop_response(None)], max_iterations=1)
        assert ua._invocation_stats == []

    @pytest.mark.asyncio
    async def test_main_loop__single_call__appends_one_entry(self):
        loop_response = _make_loop_response(
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            )
        )
        ua = _build_run_ua([loop_response], max_iterations=1)

        await ua.run()

        assert len(ua._invocation_stats) == 1
        entry = ua._invocation_stats[0]
        assert entry.model_name == MODEL_NAME
        assert entry.source == "main_loop"
        assert entry.token_usage == LanguageModelTokenUsage(
            completion_tokens=10, prompt_tokens=20, total_tokens=30
        )

    @pytest.mark.asyncio
    async def test_main_loop__multiple_iterations__appends_one_entry_per_call(self):
        tool_call = MagicMock()
        tool_call.name = "WebSearch"

        first = _make_loop_response(
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            )
        )
        first.tool_calls = [tool_call]
        second = _make_loop_response(
            LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=2, total_tokens=3
            )
        )
        ua = _build_run_ua([first, second], max_iterations=2)
        ua._tool_manager.execute_selected_tools = AsyncMock(
            return_value=[
                ToolCallResponse(id="call_1", name="WebSearch", invocation_stats=[])
            ]
        )

        await ua.run()

        assert len(ua._invocation_stats) == 2
        assert [entry.token_usage.total_tokens for entry in ua._invocation_stats] == [
            30,
            3,
        ]
        assert all(entry.source == "main_loop" for entry in ua._invocation_stats)

    @pytest.mark.asyncio
    async def test_main_loop__none_mixed_with_real__none_is_skipped(self):
        tool_call = MagicMock()
        tool_call.name = "WebSearch"

        first = _make_loop_response(
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            )
        )
        first.tool_calls = [tool_call]
        second = _make_loop_response(None)
        ua = _build_run_ua([first, second], max_iterations=2)
        ua._tool_manager.execute_selected_tools = AsyncMock(
            return_value=[
                ToolCallResponse(id="call_1", name="WebSearch", invocation_stats=[])
            ]
        )

        await ua.run()

        assert len(ua._invocation_stats) == 1
        assert ua._invocation_stats[0].token_usage == LanguageModelTokenUsage(
            completion_tokens=10, prompt_tokens=20, total_tokens=30
        )


class TestRunTokenUsageIntegration:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__debug_info_manager__receives_llm_invocations_key(self):
        """A single-iteration run with real usage on the loop response must
        surface it under debug_info's 'llm_invocations' key."""
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
        assert "llm_invocations" in calls_by_key
        payload = calls_by_key["llm_invocations"]
        assert payload["totalTokenUsage"] == {
            "completionTokens": 12,
            "promptTokens": 34,
            "totalTokens": 46,
            "reasoningTokens": None,
            "cachedTokens": None,
            "cacheWriteTokens": None,
        }
        assert len(payload["invocations"]) == 1
        assert payload["invocations"][0]["modelName"] == MODEL_NAME
        assert payload["invocations"][0]["source"] == "main_loop"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__no_usage_on_any_response__llm_invocations_report_is_empty(
        self,
    ):
        """When usage is never populated (e.g. no supporting provider),
        the 'llm_invocations' key must still be present with an empty report,
        not absent/silent."""
        ua = _build_run_ua([_make_loop_response(None)], max_iterations=1)

        await ua.run()

        calls_by_key = {
            args[0][0]: args[0][1] for args in ua._debug_info_manager.add.call_args_list
        }
        assert "llm_invocations" in calls_by_key
        assert calls_by_key["llm_invocations"] == {
            "invocations": [],
            "totalTokenUsage": None,
        }

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__postprocessor_usage__added_to_loop_usage(self):
        """FollowUpPostprocessor (and any postprocessor) makes its own LLM
        call outside _plan_or_execute() -- its usage must be added to the
        same total, not silently dropped."""
        loop_response = _make_loop_response(
            LanguageModelTokenUsage(
                completion_tokens=12, prompt_tokens=34, total_tokens=46
            )
        )
        ua = _build_run_ua([loop_response], max_iterations=1)
        ua._postprocessor_manager.get_invocation_stats.return_value = [
            LanguageModelInvocationStats.from_usage(
                MODEL_NAME,
                LanguageModelTokenUsage(
                    completion_tokens=3, prompt_tokens=7, total_tokens=10
                ),
                source="FollowUpPostprocessor",
            )
        ]

        await ua.run()

        calls_by_key = {
            args[0][0]: args[0][1] for args in ua._debug_info_manager.add.call_args_list
        }
        payload = calls_by_key["llm_invocations"]
        assert payload["totalTokenUsage"] == {
            "completionTokens": 15,
            "promptTokens": 41,
            "totalTokens": 56,
            "reasoningTokens": None,
            "cachedTokens": None,
            "cacheWriteTokens": None,
        }
        sources = [inv["source"] for inv in payload["invocations"]]
        assert sources == ["main_loop", "FollowUpPostprocessor"]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__loop_runner_reports_invocation_stats__added_to_loop_usage(
        self,
    ):
        """PlanningMiddleware (and any loop-runner wrapper implementing
        SupportsInvocationStats) makes its own LLM call outside the main
        completion -- e.g. a planning step before the iteration -- and its
        usage must be folded into the same total, not silently dropped."""
        loop_response = _make_loop_response(
            LanguageModelTokenUsage(
                completion_tokens=12, prompt_tokens=34, total_tokens=46
            )
        )
        ua = _build_run_ua([loop_response], max_iterations=1)
        # A bare AsyncMock() satisfies hasattr() for any name but does NOT
        # satisfy isinstance() against a runtime_checkable Protocol -- only
        # spec=<the protocol> does, matching what real PlanningMiddleware
        # instances trigger via isinstance() in production.
        runner = AsyncMock(spec=SupportsInvocationStats)
        runner.side_effect = [loop_response]
        runner.get_invocation_stats.return_value = [
            LanguageModelInvocationStats.from_usage(
                MODEL_NAME,
                LanguageModelTokenUsage(
                    completion_tokens=2, prompt_tokens=8, total_tokens=10
                ),
                source="planning",
            )
        ]
        ua._loop_iteration_runner = runner

        await ua.run()

        calls_by_key = {
            args[0][0]: args[0][1] for args in ua._debug_info_manager.add.call_args_list
        }
        payload = calls_by_key["llm_invocations"]
        assert payload["totalTokenUsage"] == {
            "completionTokens": 14,
            "promptTokens": 42,
            "totalTokens": 56,
            "reasoningTokens": None,
            "cachedTokens": None,
            "cacheWriteTokens": None,
        }
        sources = [inv["source"] for inv in payload["invocations"]]
        assert sources == ["main_loop", "planning"]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__loop_runner_without_invocation_stats__is_a_noop(self):
        """A plain runner that doesn't implement SupportsInvocationStats
        (the common case: Basic/Qwen/Mistral runners with no planning
        middleware) must not contribute spurious entries."""
        loop_response = _make_loop_response(
            LanguageModelTokenUsage(
                completion_tokens=12, prompt_tokens=34, total_tokens=46
            )
        )
        ua = _build_run_ua([loop_response], max_iterations=1)
        # spec restricts this mock to only __call__ -- no get_invocation_stats
        # attribute exists, so isinstance(..., SupportsInvocationStats) is False,
        # mirroring a real runner (Basic/Qwen/Mistral) that doesn't implement it.
        ua._loop_iteration_runner = AsyncMock(
            side_effect=[loop_response], spec=["__call__"]
        )

        await ua.run()

        calls_by_key = {
            args[0][0]: args[0][1] for args in ua._debug_info_manager.add.call_args_list
        }
        payload = calls_by_key["llm_invocations"]
        sources = [inv["source"] for inv in payload["invocations"]]
        assert sources == ["main_loop"]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__tool_usage__added_to_loop_usage(self):
        """A tool's own internal LLM calls (e.g. web search argument screening)
        report usage via ToolCallResponse.invocation_stats -- it must be folded
        into the same total as the main loop, per tool-call iteration."""
        tool_call = MagicMock()
        tool_call.name = "WebSearch"

        loop_response_with_tools = _make_loop_response(
            LanguageModelTokenUsage(
                completion_tokens=12, prompt_tokens=34, total_tokens=46
            )
        )
        loop_response_with_tools.tool_calls = [tool_call]
        loop_response_with_tools.is_empty.return_value = False

        final_response = _make_loop_response(None)

        ua = _build_run_ua([loop_response_with_tools, final_response], max_iterations=2)
        ua._tool_manager.execute_selected_tools = AsyncMock(
            return_value=[
                ToolCallResponse(
                    id="call_1",
                    name="WebSearch",
                    invocation_stats=[
                        LanguageModelInvocationStats.from_usage(
                            MODEL_NAME,
                            LanguageModelTokenUsage(
                                completion_tokens=1, prompt_tokens=2, total_tokens=3
                            ),
                            source="WebSearch",
                        )
                    ],
                )
            ]
        )

        await ua.run()

        calls_by_key = {
            args[0][0]: args[0][1] for args in ua._debug_info_manager.add.call_args_list
        }
        payload = calls_by_key["llm_invocations"]
        assert payload["totalTokenUsage"] == {
            "completionTokens": 13,
            "promptTokens": 36,
            "totalTokens": 49,
            "reasoningTokens": None,
            "cachedTokens": None,
            "cacheWriteTokens": None,
        }
        sources = [inv["source"] for inv in payload["invocations"]]
        assert sources == ["main_loop", "WebSearch"]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__multiple_tool_calls_in_one_iteration__usage_summed(self):
        """Two (or more) tool calls in the same iteration -- e.g. two parallel
        web searches -- must each contribute their own usage, not overwrite
        or drop one another."""
        tool_call = MagicMock()
        tool_call.name = "WebSearch"

        loop_response_with_tools = _make_loop_response(None)
        loop_response_with_tools.tool_calls = [tool_call, tool_call]
        loop_response_with_tools.is_empty.return_value = False

        final_response = _make_loop_response(None)

        ua = _build_run_ua([loop_response_with_tools, final_response], max_iterations=2)
        ua._tool_manager.execute_selected_tools = AsyncMock(
            return_value=[
                ToolCallResponse(
                    id="call_1",
                    name="WebSearch",
                    invocation_stats=[
                        LanguageModelInvocationStats.from_usage(
                            MODEL_NAME,
                            LanguageModelTokenUsage(
                                completion_tokens=1, prompt_tokens=2, total_tokens=3
                            ),
                            source="WebSearch",
                        )
                    ],
                ),
                ToolCallResponse(
                    id="call_2",
                    name="WebSearch",
                    invocation_stats=[
                        LanguageModelInvocationStats.from_usage(
                            MODEL_NAME,
                            LanguageModelTokenUsage(
                                completion_tokens=4, prompt_tokens=5, total_tokens=9
                            ),
                            source="WebSearch",
                        )
                    ],
                ),
            ]
        )

        await ua.run()

        calls_by_key = {
            args[0][0]: args[0][1] for args in ua._debug_info_manager.add.call_args_list
        }
        payload = calls_by_key["llm_invocations"]
        assert payload["totalTokenUsage"] == {
            "completionTokens": 5,
            "promptTokens": 7,
            "totalTokens": 12,
            "reasoningTokens": None,
            "cachedTokens": None,
            "cacheWriteTokens": None,
        }
        assert len(payload["invocations"]) == 2

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__reset_between_runs__does_not_leak_across_calls(self):
        """_invocation_stats must reset at the start of run(), so a second run()
        on the same UniqueAI instance doesn't inherit the prior run's entries."""
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
        payload = calls_by_key["llm_invocations"]
        assert payload["totalTokenUsage"] == {
            "completionTokens": 5,
            "promptTokens": 5,
            "totalTokens": 10,
            "reasoningTokens": None,
            "cachedTokens": None,
            "cacheWriteTokens": None,
        }
        assert len(payload["invocations"]) == 1
