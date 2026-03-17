import time
from unittest.mock import AsyncMock, MagicMock

import pytest


def _build_unique_ai(**overrides):
    """Build a minimal UniqueAI with all dependencies mocked."""
    from unique_orchestrator.unique_ai import UniqueAI

    mock_tool_manager = MagicMock()
    mock_tool_manager.available_tools = []
    mock_tool_manager.filter_duplicate_tool_calls.side_effect = lambda x: x
    mock_tool_manager.filter_tool_calls_by_max_tool_calls_allowed.side_effect = (
        lambda x: x
    )
    mock_tool_manager.does_a_tool_take_control.return_value = False
    mock_tool_manager.should_stop_after_tool_calls.return_value = False
    mock_tool_manager.get_evaluation_check_list.return_value = []

    mock_chat_service = MagicMock()
    mock_chat_service.update_debug_info_async = AsyncMock(return_value=None)
    mock_chat_service.get_debug_info_async = AsyncMock(return_value={})

    dummy_event = MagicMock()
    dummy_event.payload.assistant_message.id = "assist_1"
    dummy_event.payload.user_message.text = "query"
    dummy_event.payload.assistant_id = "assistant_123"
    dummy_event.payload.name = "TestAssistant"
    dummy_event.payload.user_metadata = {"key": "value"}
    dummy_event.payload.tool_parameters = {"param": "value"}

    mock_config = MagicMock()
    mock_config.agent.prompt_config.user_metadata = []

    mock_debug_info_manager = MagicMock()
    mock_debug_info_manager.get.return_value = {}

    defaults = dict(
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
        history_manager=MagicMock(),
        evaluation_manager=MagicMock(),
        postprocessor_manager=MagicMock(),
        message_step_logger=MagicMock(),
        mcp_servers=[],
        loop_iteration_runner=MagicMock(),
    )
    defaults.update(overrides)
    return UniqueAI(**defaults)


def _make_tool_response(name: str, execution_time_s: float | None = None) -> MagicMock:
    response = MagicMock()
    response.name = name
    response.debug_info = (
        {"execution_time_s": execution_time_s} if execution_time_s is not None else None
    )
    return response


def _make_loop_response(tool_calls: list | None = None) -> MagicMock:
    response = MagicMock()
    response.tool_calls = tool_calls or []
    response.message = MagicMock()
    response.message.references = []
    response.message.text = "response text"
    response.is_empty.return_value = False
    return response


class TestFinalizeLoopTiming:
    """Unit tests for UniqueAI._finalize_loop_timing."""

    @pytest.fixture
    def mock_unique_ai(self):
        return _build_unique_ai()

    @pytest.mark.ai
    def test_init__execution_times__is_empty_list(self, mock_unique_ai) -> None:
        """
        Purpose: Verify that _execution_times is initialised as an empty list.
        Why this matters: An uninitialised list would cause AttributeError on the first
        append in _finalize_loop_timing.
        Setup summary: Freshly constructed UniqueAI; assert _execution_times == [].
        """
        assert mock_unique_ai._execution_times == []

    @pytest.mark.ai
    def test_init__current_loop_timing__is_empty_dict(self, mock_unique_ai) -> None:
        """
        Purpose: Verify that _current_loop_timing is initialised as an empty dict.
        Why this matters: Code in _handle_tool_calls and _handle_no_tool_calls writes
        into this dict assuming it exists; a missing attribute would raise AttributeError.
        Setup summary: Freshly constructed UniqueAI; assert _current_loop_timing == {}.
        """
        assert mock_unique_ai._current_loop_timing == {}

    @pytest.mark.ai
    def test_finalize_loop_timing__total_loop_time__added_to_timing_dict(
        self, mock_unique_ai
    ) -> None:
        """
        Purpose: Verify that total_loop_time is computed and stored after finalization.
        Why this matters: total_loop_time is the primary KPI consumers read to understand
        overall iteration cost; a missing key would cause KeyError downstream.
        Setup summary: Seed _current_loop_timing with a known entry; call
        _finalize_loop_timing with a start time 1 s in the past; assert key present
        and value >= 1.0.
        """
        mock_unique_ai._current_loop_timing = {
            "iteration": 1,
            "planning_or_streaming": 0.5,
        }
        loop_start = time.perf_counter() - 1.0
        mock_unique_ai._finalize_loop_timing(loop_start)

        assert "total_loop_time" in mock_unique_ai._current_loop_timing
        assert mock_unique_ai._current_loop_timing["total_loop_time"] >= 1.0

    @pytest.mark.ai
    def test_finalize_loop_timing__execution_times__receives_a_copy(
        self, mock_unique_ai
    ) -> None:
        """
        Purpose: Verify that _finalize_loop_timing appends a shallow copy, not the
        live reference to _current_loop_timing.
        Why this matters: Appending the reference means subsequent mutations of
        _current_loop_timing (next iteration setup) would silently corrupt earlier
        entries in _execution_times.
        Setup summary: Call _finalize_loop_timing; assert the appended entry equals the
        dict but is not the same object.
        """
        mock_unique_ai._current_loop_timing = {
            "iteration": 1,
            "planning_or_streaming": 0.5,
        }
        mock_unique_ai._finalize_loop_timing(time.perf_counter())

        assert len(mock_unique_ai._execution_times) == 1
        assert mock_unique_ai._execution_times[0] == mock_unique_ai._current_loop_timing
        assert (
            mock_unique_ai._execution_times[0]
            is not mock_unique_ai._current_loop_timing
        )

    @pytest.mark.ai
    def test_finalize_loop_timing__execution_times__accumulates_across_calls(
        self, mock_unique_ai
    ) -> None:
        """
        Purpose: Verify that repeated calls across iterations append independent entries.
        Why this matters: A multi-iteration run must produce one timing entry per
        iteration; any overwrite or sharing would produce incorrect aggregates.
        Setup summary: Call _finalize_loop_timing twice with different dicts; assert
        len == 2 and each entry has the correct iteration number.
        """
        mock_unique_ai._current_loop_timing = {
            "iteration": 1,
            "planning_or_streaming": 0.3,
        }
        mock_unique_ai._finalize_loop_timing(time.perf_counter())

        mock_unique_ai._current_loop_timing = {
            "iteration": 2,
            "planning_or_streaming": 0.7,
        }
        mock_unique_ai._finalize_loop_timing(time.perf_counter())

        assert len(mock_unique_ai._execution_times) == 2
        assert mock_unique_ai._execution_times[0]["iteration"] == 1
        assert mock_unique_ai._execution_times[1]["iteration"] == 2

    @pytest.mark.ai
    def test_finalize_loop_timing__total_loop_time__rounded_to_three_decimals(
        self, mock_unique_ai
    ) -> None:
        """
        Purpose: Verify that total_loop_time is rounded to exactly 3 decimal places.
        Why this matters: Consumers of the debug info expect a compact float; excessive
        precision inflates stored JSON and makes values hard to compare in tests.
        Setup summary: Call _finalize_loop_timing; assert round(total, 3) == total.
        """
        mock_unique_ai._current_loop_timing = {"iteration": 1}
        mock_unique_ai._finalize_loop_timing(time.perf_counter())

        total = mock_unique_ai._current_loop_timing["total_loop_time"]
        assert total == round(total, 3)

    @pytest.mark.ai
    def test_finalize_loop_timing__existing_keys__preserved_in_appended_entry(
        self, mock_unique_ai
    ) -> None:
        """
        Purpose: Verify that keys written by earlier phases are intact in the final entry.
        Why this matters: The full timing dict is only useful if planning, tool, post-
        processing, and evaluation times all survive the finalization step.
        Setup summary: Pre-populate all timing sub-keys; finalize; assert every
        sub-key appears with its original value in _execution_times[0].
        """
        mock_unique_ai._current_loop_timing = {
            "iteration": 1,
            "planning_or_streaming": 0.5,
            "post_processing": {"source_handler": 0.2},
            "evaluation": {"hallucination": 0.3},
            "tool_execution": {"total": 1.5, "search": 0.8},
        }
        mock_unique_ai._finalize_loop_timing(time.perf_counter())

        timing = mock_unique_ai._execution_times[0]
        assert timing["iteration"] == 1
        assert timing["planning_or_streaming"] == 0.5
        assert timing["post_processing"] == {"source_handler": 0.2}
        assert timing["evaluation"] == {"hallucination": 0.3}
        assert timing["tool_execution"] == {"total": 1.5, "search": 0.8}
        assert "total_loop_time" in timing


class TestHandleToolCallsTiming:
    """Tests that _handle_tool_calls populates _current_loop_timing['tool_execution']."""

    @pytest.fixture
    def ua(self):
        instance = _build_unique_ai()
        instance._current_loop_timing = {
            "iteration": 1,
            "tool_execution": {},
            "post_processing": {},
            "evaluation": {},
        }
        return instance

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_handle_tool_calls__tool_execution_total__is_recorded(
        self, ua
    ) -> None:
        """
        Purpose: Verify that tool_execution['total'] is set to a non-negative float after
        tool execution.
        Why this matters: 'total' represents the wall-clock cost of all tool calls in one
        iteration and is the primary number used for performance analysis.
        Setup summary: Mock execute_selected_tools to return one response without timing;
        call _handle_tool_calls; assert 'total' exists and is a non-negative float.
        """
        ua._tool_manager.execute_selected_tools = AsyncMock(
            return_value=[_make_tool_response("search")]
        )
        await ua._handle_tool_calls(_make_loop_response([MagicMock()]))

        timing = ua._current_loop_timing["tool_execution"]
        assert "total" in timing
        assert isinstance(timing["total"], float)
        assert timing["total"] >= 0.0

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_handle_tool_calls__per_tool_time__captured_from_debug_info(
        self, ua
    ) -> None:
        """
        Purpose: Verify that execution_time_s from a tool's debug_info is stored under
        the tool's name inside tool_execution.
        Why this matters: Per-tool breakdown is the key value this feature adds; without
        it the only observable data is the aggregate total.
        Setup summary: Return one tool response with debug_info['execution_time_s'] = 1.23;
        assert tool_execution['search'] == 1.23.
        """
        ua._tool_manager.execute_selected_tools = AsyncMock(
            return_value=[_make_tool_response("search", execution_time_s=1.23)]
        )
        await ua._handle_tool_calls(_make_loop_response([MagicMock()]))

        assert ua._current_loop_timing["tool_execution"]["search"] == 1.23

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_handle_tool_calls__tool_without_execution_time__omitted_from_per_tool_dict(
        self, ua
    ) -> None:
        """
        Purpose: Verify that tools whose debug_info lacks execution_time_s are silently
        skipped and do not corrupt the dict.
        Why this matters: Not all tools instrument their execution time; a KeyError or
        None entry would break consumers iterating over the timing dict.
        Setup summary: Return a tool response with debug_info=None; assert the tool name
        is absent but 'total' is still present.
        """
        ua._tool_manager.execute_selected_tools = AsyncMock(
            return_value=[_make_tool_response("search", execution_time_s=None)]
        )
        await ua._handle_tool_calls(_make_loop_response([MagicMock()]))

        timing = ua._current_loop_timing["tool_execution"]
        assert "search" not in timing
        assert "total" in timing

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_handle_tool_calls__duplicate_tool_names__get_incrementing_suffix(
        self, ua
    ) -> None:
        """
        Purpose: Verify that when the same tool is called multiple times in one iteration
        each occurrence is stored under a unique key (_2, _3, …).
        Why this matters: Dict key collisions would silently discard all but the last
        timing entry for that tool, under-reporting total execution cost.
        Setup summary: Return three responses all named 'search' with distinct times;
        assert search, search_2, and search_3 all carry the correct values.
        """
        ua._tool_manager.execute_selected_tools = AsyncMock(
            return_value=[
                _make_tool_response("search", execution_time_s=1.0),
                _make_tool_response("search", execution_time_s=2.0),
                _make_tool_response("search", execution_time_s=3.0),
            ]
        )
        await ua._handle_tool_calls(_make_loop_response([MagicMock()]))

        timing = ua._current_loop_timing["tool_execution"]
        assert timing["search"] == 1.0
        assert timing["search_2"] == 2.0
        assert timing["search_3"] == 3.0

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_handle_tool_calls__multiple_distinct_tools__all_captured(
        self, ua
    ) -> None:
        """
        Purpose: Verify that different tools in the same iteration each get their own key.
        Why this matters: A loop that mixes tool types (e.g. search + calculator) must
        report individual costs so slow tools can be identified.
        Setup summary: Return two responses with different names; assert both names are
        present with their respective times.
        """
        ua._tool_manager.execute_selected_tools = AsyncMock(
            return_value=[
                _make_tool_response("search", execution_time_s=0.5),
                _make_tool_response("calculator", execution_time_s=0.1),
            ]
        )
        await ua._handle_tool_calls(_make_loop_response([MagicMock()]))

        timing = ua._current_loop_timing["tool_execution"]
        assert timing["search"] == 0.5
        assert timing["calculator"] == 0.1


class TestHandleNoToolCallsTiming:
    """Tests that _handle_no_tool_calls populates post_processing and evaluation timing."""

    @pytest.fixture
    def ua(self):
        instance = _build_unique_ai()
        instance._current_loop_timing = {
            "iteration": 1,
            "tool_execution": {},
            "post_processing": {},
            "evaluation": {},
        }
        instance._evaluation_manager.run_evaluations = AsyncMock(return_value=[])
        instance._postprocessor_manager.run_postprocessors = AsyncMock(
            return_value=None
        )
        return instance

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_handle_no_tool_calls__post_processing_times__captured_from_manager(
        self, ua
    ) -> None:
        """
        Purpose: Verify that post_processing timing is populated from
        postprocessor_manager.get_execution_times() after the gather completes.
        Why this matters: Post-processing (e.g. PDF extraction, source handling) can be
        a significant share of iteration time; missing it hides bottlenecks.
        Setup summary: Configure get_execution_times to return a known dict; assert
        _current_loop_timing['post_processing'] matches it exactly.
        """
        ua._postprocessor_manager.get_execution_times.return_value = {
            "pdf_extractor": 0.5,
            "source_handler": 0.2,
        }
        ua._tool_manager.get_evaluation_check_list.return_value = []

        await ua._handle_no_tool_calls(_make_loop_response())

        assert ua._current_loop_timing["post_processing"] == {
            "pdf_extractor": 0.5,
            "source_handler": 0.2,
        }

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_handle_no_tool_calls__evaluation_times__captured_per_selected_name(
        self, ua
    ) -> None:
        """
        Purpose: Verify that each selected evaluation name is stored with its timing value.
        Why this matters: Evaluation checks (e.g. hallucination, relevance) add latency;
        per-name visibility is needed to decide which checks to disable for latency.
        Setup summary: Configure get_evaluation_check_list to return two names and
        get_execution_times to return times for both; assert each name has the right time.
        """
        ua._tool_manager.get_evaluation_check_list.return_value = [
            "hallucination",
            "relevance",
        ]
        ua._evaluation_manager.get_execution_times.return_value = {
            "hallucination": 0.3,
            "relevance": 0.4,
        }
        ua._postprocessor_manager.get_execution_times.return_value = {}

        await ua._handle_no_tool_calls(_make_loop_response())

        assert ua._current_loop_timing["evaluation"]["hallucination"] == 0.3
        assert ua._current_loop_timing["evaluation"]["relevance"] == 0.4

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_handle_no_tool_calls__evaluation_time_missing__defaults_to_zero(
        self, ua
    ) -> None:
        """
        Purpose: Verify that a selected evaluation with no recorded time defaults to 0.
        Why this matters: An absent key in get_execution_times must not raise KeyError or
        silently omit the evaluation from the timing dict.
        Setup summary: Configure get_evaluation_check_list with one name, return empty
        get_execution_times; assert evaluation[name] == 0.
        """
        ua._tool_manager.get_evaluation_check_list.return_value = ["hallucination"]
        ua._evaluation_manager.get_execution_times.return_value = {}
        ua._postprocessor_manager.get_execution_times.return_value = {}

        await ua._handle_no_tool_calls(_make_loop_response())

        assert ua._current_loop_timing["evaluation"]["hallucination"] == 0

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_handle_no_tool_calls__unselected_evaluations__not_recorded(
        self, ua
    ) -> None:
        """
        Purpose: Verify that evaluations not in the selected list are excluded even if
        they appear in get_execution_times.
        Why this matters: Recording unselected evaluations would misrepresent which checks
        ran and inflate the evaluation timing dict with phantom entries.
        Setup summary: get_evaluation_check_list returns ['hallucination']; times contain
        an extra 'unselected_eval'; assert 'unselected_eval' is absent.
        """
        ua._tool_manager.get_evaluation_check_list.return_value = ["hallucination"]
        ua._evaluation_manager.get_execution_times.return_value = {
            "hallucination": 0.3,
            "unselected_eval": 0.9,
        }
        ua._postprocessor_manager.get_execution_times.return_value = {}

        await ua._handle_no_tool_calls(_make_loop_response())

        assert "unselected_eval" not in ua._current_loop_timing["evaluation"]


class TestRunExecutionTimingIntegration:
    """Integration tests: run() persists execution_time in debug info correctly."""

    def _build_run_ua(
        self,
        monkeypatch,
        tool_took_control: bool = False,
        include_tool_calls: bool = False,
    ):
        mock_feature_flags = MagicMock()
        monkeypatch.setattr(
            "unique_orchestrator.unique_ai.feature_flags", mock_feature_flags
        )

        mock_cancellation = MagicMock()
        mock_cancellation.is_cancelled = False
        mock_cancellation.on_cancellation.subscribe = MagicMock(
            return_value=MagicMock()
        )
        mock_cancellation.check_cancellation_async = AsyncMock(return_value=False)

        mock_chat_service = MagicMock()
        mock_chat_service.cancellation = mock_cancellation
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
        mock_tool_manager.does_a_tool_take_control.return_value = tool_took_control
        mock_tool_manager.should_stop_after_tool_calls.return_value = False
        mock_tool_manager.get_evaluation_check_list.return_value = []
        mock_tool_manager.execute_selected_tools = AsyncMock(
            return_value=[_make_tool_response("SomeTool", execution_time_s=0.1)]
        )

        mock_debug_info_manager = MagicMock()
        mock_debug_info_manager.get.return_value = {}

        mock_config = MagicMock()
        mock_config.effective_max_loop_iterations = 1
        mock_config.agent.prompt_config.user_metadata = []

        mock_history_manager = MagicMock()
        mock_history_manager.get_history_for_model_call = AsyncMock(
            return_value=MagicMock()
        )
        mock_history_manager._append_tool_calls_to_history = MagicMock()
        mock_history_manager.add_tool_call_results = MagicMock()

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

        loop_response = _make_loop_response(
            tool_calls=[MagicMock(name="tool_call")] if include_tool_calls else None
        )
        if not include_tool_calls:
            loop_response.tool_calls = None

        from unique_orchestrator.unique_ai import UniqueAI

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
            loop_iteration_runner=AsyncMock(return_value=loop_response),
        )
        ua._render_user_prompt = AsyncMock(return_value="user")  # type: ignore[method-assign]
        ua._render_system_prompt = AsyncMock(return_value="system")  # type: ignore[method-assign]
        ua._thinking_manager.thinking_is_displayed = MagicMock(return_value=True)
        return ua

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__debug_info_manager__receives_execution_time_key(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that run() calls debug_info_manager.add with 'execution_time'
        containing loop_iterations and total_time after the agentic loop completes.
        Why this matters: This is the primary write path for timing data; if the key is
        missing or structured incorrectly no timing is ever persisted.
        Setup summary: Run one iteration; assert debug_info_manager.add was called once
        with 'execution_time' as the first argument.
        """
        ua = self._build_run_ua(monkeypatch)

        await ua.run()

        call_args = ua._debug_info_manager.add.call_args
        assert call_args[0][0] == "execution_time"
        payload = call_args[0][1]
        assert "loop_iterations" in payload
        assert "total_time" in payload

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__execution_times__contains_one_entry_after_single_iteration(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that a single-iteration run produces exactly one timing entry
        with the correct iteration number and all expected keys.
        Why this matters: The loop_iterations list is the per-request breakdown; an
        incorrect count or missing keys would make the data unusable.
        Setup summary: Run with effective_max_loop_iterations=1; assert len == 1 and
        entry has 'iteration', 'total_loop_time', and 'planning_or_streaming'.
        """
        ua = self._build_run_ua(monkeypatch)

        await ua.run()

        assert len(ua._execution_times) == 1
        entry = ua._execution_times[0]
        assert entry["iteration"] == 1
        assert "total_loop_time" in entry
        assert "planning_or_streaming" in entry

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__iteration_timing__includes_all_expected_keys(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that every timing sub-category key is present in the final entry.
        Why this matters: Consumers iterate over all keys; a missing key causes a silent
        gap in the timing report or a KeyError in downstream processing.
        Setup summary: Run one iteration; assert all six expected keys are in the entry.
        """
        ua = self._build_run_ua(monkeypatch)

        await ua.run()

        entry = ua._execution_times[0]
        for key in (
            "iteration",
            "planning_or_streaming",
            "tool_execution",
            "post_processing",
            "evaluation",
            "total_loop_time",
        ):
            assert key in entry, f"expected key '{key}' missing from timing entry"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__update_debug_info_async__called_once_when_no_tool_control(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that update_debug_info_async is called exactly once when no tool
        takes control (the common path).
        Why this matters: Multiple writes with inconsistent payloads could clobber timing
        data or create a race condition if the service is remote.
        Setup summary: does_a_tool_take_control=False; run; assert call_count == 1.
        """
        ua = self._build_run_ua(monkeypatch, tool_took_control=False)

        await ua.run()

        assert ua._chat_service.update_debug_info_async.call_count == 1

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__update_debug_info_async__called_once_when_tool_took_control(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that update_debug_info_async is called exactly once even when a
        tool takes control of the conversation.
        Why this matters: Before the guard was added, two writes occurred in this path:
        the unconditional write plus the one inside _update_debug_info_if_tool_took_control,
        wasting a round-trip and risking stale data overwrites.
        Setup summary: does_a_tool_take_control=True with one tool_call in loop_response;
        run; assert tool execution path ran and update_debug_info_async called once.
        """
        ua = self._build_run_ua(
            monkeypatch,
            tool_took_control=True,
            include_tool_calls=True,
        )
        ua._debug_info_manager.get.return_value = {"tools": [{"name": "SomeTool"}]}

        await ua.run()

        ua._tool_manager.execute_selected_tools.assert_called_once()
        assert ua._tool_took_control is True
        assert ua._chat_service.update_debug_info_async.call_count == 1

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__debug_info_update_failure__does_not_block_completion(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that a failure in update_debug_info_async does not prevent
        assistant message completion.
        Why this matters: Debug info persistence is diagnostic; users should still get a
        completed message even if debug info write fails.
        Setup summary: Make update_debug_info_async raise; run one iteration; assert
        modify_assistant_message_async is still called.
        """
        ua = self._build_run_ua(monkeypatch)
        ua._chat_service.update_debug_info_async.side_effect = RuntimeError("boom")

        await ua.run()

        ua._chat_service.modify_assistant_message_async.assert_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__cancellation_after_process_plan__does_not_duplicate_timing_entry(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that if cancellation is detected after process_plan, timing is
        finalized only once for the iteration.
        Why this matters: Duplicate timing entries inflate loop_iterations and misreport
        iteration-level performance in debug info.
        Setup summary: Configure cancellation checks as [False, False, True] to cancel
        right after finalization point; run; assert exactly one timing entry.
        """
        ua = self._build_run_ua(monkeypatch)
        ua._chat_service.cancellation.check_cancellation_async = AsyncMock(
            side_effect=[False, False, True]
        )

        await ua.run()

        assert len(ua._execution_times) == 1


class TestCancellationTimingShape:
    """Timing entries produced on cancellation have a consistent dict shape."""

    @pytest.mark.ai
    def test_cancelled_iteration__timing_entry__has_all_expected_keys(self) -> None:
        """
        Purpose: Verify that an iteration cancelled before tool execution still produces
        an entry with tool_execution, post_processing, evaluation, and total_loop_time.
        Why this matters: Consumers expect a uniform dict shape across all entries;
        missing keys on cancelled iterations would require defensive get() calls everywhere.
        Setup summary: Initialise _current_loop_timing with the standard initial dict
        (tool_execution: {}, post_processing: {}, evaluation: {}); finalize; assert all
        expected keys are present.
        """
        ua = _build_unique_ai()
        ua._current_loop_timing = {
            "iteration": 1,
            "tool_execution": {},
            "post_processing": {},
            "evaluation": {},
        }
        ua._finalize_loop_timing(time.perf_counter())

        entry = ua._execution_times[0]
        for key in (
            "tool_execution",
            "post_processing",
            "evaluation",
            "total_loop_time",
        ):
            assert key in entry, (
                f"expected key '{key}' missing from cancelled-iteration entry"
            )

    @pytest.mark.ai
    def test_cancelled_and_normal_iterations__shared_keys__are_identical(self) -> None:
        """
        Purpose: Verify that a normal iteration and a cancelled one share the same set
        of keys (minus planning_or_streaming which is absent on early cancellation).
        Why this matters: Any key present in a normal entry but absent in a cancelled one
        forces callers to special-case cancellation, leaking an internal invariant.
        Setup summary: Finalize one full timing dict and one cancellation-only dict; assert
        the sets of keys (excluding planning_or_streaming) are equal.
        """
        ua = _build_unique_ai()

        ua._current_loop_timing = {
            "iteration": 1,
            "planning_or_streaming": 0.5,
            "tool_execution": {"total": 1.0, "search": 0.8},
            "post_processing": {"pdf": 0.2},
            "evaluation": {"hallucination": 0.3},
        }
        ua._finalize_loop_timing(time.perf_counter())

        ua._current_loop_timing = {
            "iteration": 2,
            "tool_execution": {},
            "post_processing": {},
            "evaluation": {},
        }
        ua._finalize_loop_timing(time.perf_counter())

        normal_keys = set(ua._execution_times[0].keys()) - {"planning_or_streaming"}
        cancelled_keys = set(ua._execution_times[1].keys())
        assert normal_keys == cancelled_keys
