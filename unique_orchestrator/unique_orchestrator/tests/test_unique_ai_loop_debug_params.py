"""Tests for _loop_debug_params — per-iteration debug info tracking.

Covers initialisation, per-call accumulation in _plan_or_execute (both
completions-API and responses-API thinking-level extraction), and the final
write of ``loop_params`` to the debug info manager in run().
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _build_unique_ai(**overrides):
    """Return a minimal UniqueAI with all external dependencies mocked."""
    from unique_orchestrator.unique_ai import UniqueAI

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

    mock_chat_service = MagicMock()
    mock_chat_service.update_debug_info_async = AsyncMock(return_value=None)
    mock_chat_service.get_debug_info_async = AsyncMock(return_value={})

    dummy_event = MagicMock()
    dummy_event.payload.assistant_message.id = "assist_1"
    dummy_event.payload.user_message.text = "query"
    dummy_event.payload.assistant_id = "assistant_123"
    dummy_event.payload.name = "TestAssistant"
    dummy_event.payload.user_metadata = {}
    dummy_event.payload.tool_parameters = {}

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


def _make_loop_response() -> MagicMock:
    response = MagicMock()
    response.tool_calls = None
    response.message = MagicMock()
    response.message.references = []
    response.message.text = "response text"
    response.message.original_text = "original response text"
    response.is_empty.return_value = False
    response.usage = None
    return response


async def _call_plan_or_execute(ua, monkeypatch, other_options: dict) -> None:
    """Call _plan_or_execute with a patched resolve_other_options."""
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai.resolve_other_options",
        lambda *_args, **_kwargs: other_options,
    )
    ua._compose_message_plan_execution = AsyncMock(return_value=[])  # type: ignore[method-assign]
    ua._loop_iteration_runner = AsyncMock(return_value=_make_loop_response())
    await ua._plan_or_execute()


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


class TestLoopDebugParamsInit:
    @pytest.mark.ai
    def test_init__loop_debug_params__is_empty_list(self) -> None:
        """
        Purpose: Verify that _loop_debug_params is initialised as an empty list.
        Why this matters: An uninitialised attribute causes AttributeError on the
        first append inside _plan_or_execute.
        Setup summary: Freshly constructed UniqueAI; assert _loop_debug_params == [].
        """
        ua = _build_unique_ai()
        assert ua._loop_debug_params == []


# ---------------------------------------------------------------------------
# _plan_or_execute — thinking-level extraction
# ---------------------------------------------------------------------------


class TestPlanOrExecuteLoopDebugParams:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_plan_or_execute__completions_api__reasoning_effort_stored(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that a ``reasoning_effort`` value from the completions API
        is stored as ``thinking_level`` in the appended entry.
        Why this matters: The completions API uses a flat ``reasoning_effort`` key;
        the extractor must read from there, not from ``reasoning.effort``.
        Setup summary: Patch resolve_other_options to return
        ``{'reasoning_effort': 'high'}``; call _plan_or_execute; assert
        _loop_debug_params[0]['thinking_level'] == 'high'.
        """
        ua = _build_unique_ai()
        await _call_plan_or_execute(ua, monkeypatch, {"reasoning_effort": "high"})

        assert len(ua._loop_debug_params) == 1
        assert ua._loop_debug_params[0]["thinking_level"] == "high"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_plan_or_execute__responses_api__reasoning_effort_stored(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that ``reasoning.effort`` from the responses API is stored
        as ``thinking_level``.
        Why this matters: The responses API nests the effort inside a ``reasoning``
        dict; failing to look there would always produce None for responses-API calls.
        Setup summary: Patch resolve_other_options to return
        ``{'reasoning': {'effort': 'low'}}``; assert thinking_level == 'low'.
        """
        ua = _build_unique_ai()
        await _call_plan_or_execute(ua, monkeypatch, {"reasoning": {"effort": "low"}})

        assert len(ua._loop_debug_params) == 1
        assert ua._loop_debug_params[0]["thinking_level"] == "low"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_plan_or_execute__no_thinking_level__none_string_stored(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that when resolve_other_options returns no reasoning-related
        keys, thinking_level is stored as the string "None".
        Why this matters: Using the string "None" instead of Python None keeps the
        debug payload consistently typed as str, which serialises cleanly to JSON
        and is unambiguous in log output.
        Setup summary: Patch resolve_other_options to return {}; assert
        thinking_level == "None".
        """
        ua = _build_unique_ai()
        await _call_plan_or_execute(ua, monkeypatch, {})

        assert len(ua._loop_debug_params) == 1
        assert ua._loop_debug_params[0]["thinking_level"] == "None"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_plan_or_execute__loop_number__matches_current_iteration_index(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that loop_number in the appended entry equals
        current_iteration_index at call time.
        Why this matters: Consumers use loop_number to correlate debug params with
        execution timing entries; a wrong value breaks that correlation.
        Setup summary: Set current_iteration_index to 3; call _plan_or_execute;
        assert loop_number == 3.
        """
        ua = _build_unique_ai()
        ua.current_iteration_index = 3
        await _call_plan_or_execute(ua, monkeypatch, {"reasoning_effort": "medium"})

        assert ua._loop_debug_params[0]["loop_number"] == 3

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_plan_or_execute__multiple_calls__accumulates_entries_in_order(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that repeated calls across iterations append independent
        entries in the correct order.
        Why this matters: A multi-iteration run must produce one entry per iteration
        with no overwrites or entry merges.
        Setup summary: Call _plan_or_execute twice with different iteration indices
        and thinking levels; assert len == 2 and each entry has the correct values.
        """
        ua = _build_unique_ai()

        monkeypatch.setattr(
            "unique_orchestrator.unique_ai.resolve_other_options",
            lambda *_args, **_kwargs: {"reasoning_effort": "high"},
        )
        ua._compose_message_plan_execution = AsyncMock(return_value=[])  # type: ignore[method-assign]
        ua._loop_iteration_runner = AsyncMock(return_value=_make_loop_response())
        ua.current_iteration_index = 0
        await ua._plan_or_execute()

        monkeypatch.setattr(
            "unique_orchestrator.unique_ai.resolve_other_options",
            lambda *_args, **_kwargs: {"reasoning": {"effort": "low"}},
        )
        ua.current_iteration_index = 1
        await ua._plan_or_execute()

        assert len(ua._loop_debug_params) == 2
        assert ua._loop_debug_params[0] == {"loop_number": 0, "thinking_level": "high"}
        assert ua._loop_debug_params[1] == {"loop_number": 1, "thinking_level": "low"}


# ---------------------------------------------------------------------------
# run() integration — loop_params written to debug info manager
# ---------------------------------------------------------------------------


class TestRunLoopDebugParams:
    def _build_run_ua(self, monkeypatch):
        mock_feature_flags = MagicMock()
        monkeypatch.setattr(
            "unique_orchestrator.unique_ai.feature_flags", mock_feature_flags
        )
        monkeypatch.setattr(
            "unique_orchestrator.unique_ai.resolve_other_options",
            lambda *_args, **_kwargs: {"reasoning_effort": "high"},
        )

        mock_cancellation = MagicMock()
        mock_cancellation.is_cancelled = False
        mock_cancellation.on_cancellation.subscribe = MagicMock(
            return_value=MagicMock()
        )
        mock_cancellation.check_cancellation_async = AsyncMock(return_value=False)

        mock_chat_service = MagicMock()
        mock_chat_service.cancellation = mock_cancellation
        mock_chat_service.get_debug_info_async = AsyncMock(return_value={})
        mock_chat_service.update_debug_info_async = AsyncMock(return_value=None)
        # Returns None by default → no completed_at, so total_time_to_answer_ms
        # resolves to None. Tests that exercise timing override this return value
        # with a MagicMock(completed_at=...).
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
        mock_config.effective_max_loop_iterations = 1
        mock_config.agent.prompt_config.user_metadata = []
        mock_config.space.language_model.name = "AZURE_GPT_5_2025_0807"
        mock_config.space.language_model.family = "openai"
        mock_config.space.language_model.provider = "AZURE"

        mock_history_manager = MagicMock()
        mock_history_manager.get_history_for_model_call = AsyncMock(
            return_value=MagicMock()
        )
        mock_history_manager.add_tool_call_results = MagicMock()
        mock_history_manager.extract_message_tools.return_value = []

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

        loop_response = _make_loop_response()

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
    async def test_run__debug_info_manager__receives_loop_params_key(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that run() calls debug_info_manager.add with 'loop_params'
        after the agentic loop completes.
        Why this matters: Without this call, loop-level debug params are never
        persisted and the feature has no observable effect.
        Setup summary: Run one iteration; assert add was called with 'loop_params'
        as the first argument.
        """
        ua = self._build_run_ua(monkeypatch)
        tool = MagicMock()
        tool.name = "InternalSearch"
        tool.display_name.return_value = "Knowledge Base Search"
        ua._tool_manager.available_tools = [tool]

        await ua.run()

        keys_written = [
            call.args[0] for call in ua._debug_info_manager.add.call_args_list
        ]
        assert "loop_params" in keys_written
        assert "skills" in keys_written
        # This test owns one contract: run() forwards the same skills value it
        # wrote under "skills" as the first positional arg to add_analytics.
        # Per-field kwargs (references / timing / lengths) are covered by the
        # focused sibling tests below, so we don't re-pin the whole call here.
        skills_call = next(
            c
            for c in ua._debug_info_manager.add.call_args_list
            if c.args[0] == "skills"
        )
        ua._debug_info_manager.add_analytics.assert_called_once()
        analytics_call = ua._debug_info_manager.add_analytics.call_args
        assert analytics_call.args[0] == skills_call.args[1]
        assert analytics_call.kwargs["tool_display_names"] == {
            "InternalSearch": "Knowledge Base Search"
        }

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__analytics__counts_unique_reference_sources(
        self, monkeypatch
    ) -> None:
        ua = self._build_run_ua(monkeypatch)
        references = [
            MagicMock(url="source_1"),
            MagicMock(url="source_1"),
            MagicMock(url="source_2"),
            MagicMock(url="source_3"),
            MagicMock(url="source_3"),
        ]
        ua._loop_iteration_runner.return_value.message.references = references
        ua._reference_manager.get_references.return_value = [references]

        await ua.run()

        analytics_call = ua._debug_info_manager.add_analytics.call_args
        assert analytics_call.kwargs["references"] == 3

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__analytics__counts_references_across_iterations(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify analytics includes reference sources from every loop iteration.
        Why this matters: Earlier citations belong to the same run and must not be
        omitted when a later iteration appends another reference batch.
        Setup summary: Return two stored batches with one duplicate source and assert
        that all three distinct sources are counted.
        """
        ua = self._build_run_ua(monkeypatch)
        first_iteration_references = [
            MagicMock(url="source_1"),
            MagicMock(url="source_2"),
        ]
        latest_iteration_references = [
            MagicMock(url="source_2"),
            MagicMock(url="source_3"),
        ]
        ua._reference_manager.get_references.return_value = [
            first_iteration_references,
            latest_iteration_references,
        ]

        await ua.run()

        analytics_call = ua._debug_info_manager.add_analytics.call_args
        assert analytics_call.kwargs["references"] == 3

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__analytics__counts_distinct_references_without_urls(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify URL-less references are identified by source and source ID.
        Why this matters: MCP citations can omit URLs and must not collapse into one
        analytics source.
        Setup summary: Run with two distinct URL-less references and assert both count.
        """
        ua = self._build_run_ua(monkeypatch)
        references = [
            MagicMock(url=None, source="mcp", source_id="resource_1"),
            MagicMock(url=None, source="mcp", source_id="resource_2"),
        ]
        ua._loop_iteration_runner.return_value.message.references = references
        ua._reference_manager.get_references.return_value = [references]

        await ua.run()

        analytics_call = ua._debug_info_manager.add_analytics.call_args
        assert analytics_call.kwargs["references"] == 2

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__analytics__total_time_to_answer_ms_none_without_completed_at(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify total_time_to_answer_ms is None when the completed message
        carries no completed_at.
        Why this matters: Makes the None case deliberate — run() must degrade to
        None (not crash) when completion time is unavailable, e.g. a tool took
        control. Pairs with test_run__analytics__includes_total_time_to_answer_ms
        (execution-timing suite) which covers the populated case.
        Setup summary: modify_assistant_message_async returns None (fixture default);
        assert the kwarg is present and None.
        """
        ua = self._build_run_ua(monkeypatch)

        await ua.run()

        analytics_call = ua._debug_info_manager.add_analytics.call_args
        assert analytics_call.kwargs["total_time_to_answer_ms"] is None

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__generated_files_info__reset_at_start_prevents_stale_artifacts(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify run() resets _generated_files_info at the start, so a rerun
        that exits without reaching _handle_no_tool_calls does not report the previous
        run's artifacts.
        Why this matters: _generated_files_info persists on the UniqueAI instance;
        without a reset it leaks a prior run's artifact count/filetypes into the
        current answer's analytics (Cursor bot, UN-22110).
        Setup summary: Seed a stale value, force an early loop exit via _process_plan
        returning True (a tool took control — _handle_no_tool_calls never runs), and
        assert add_analytics received artifacts=None.
        """
        ua = self._build_run_ua(monkeypatch)
        # Leftover from a hypothetical previous run on the same instance.
        ua._generated_files_info = {"count": 99, "filetypes": ["stale"]}
        # Exit the loop as if a tool took control: _handle_no_tool_calls (which sets
        # _generated_files_info) is skipped, but finalization still calls add_analytics.
        ua._process_plan = AsyncMock(return_value=True)  # type: ignore[method-assign]

        await ua.run()

        analytics_call = ua._debug_info_manager.add_analytics.call_args
        assert analytics_call.kwargs["artifacts"] is None

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__loop_params__contains_one_entry_per_iteration(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that the loop_params value written to the debug info manager
        contains exactly one entry for a single-iteration run.
        Why this matters: The entry count must match the iteration count so that
        loop_params and execution_time.loop_iterations stay in sync.
        Setup summary: Run with effective_max_loop_iterations=1; find the loop_params
        add call; assert the value is a list of length 1.
        """
        ua = self._build_run_ua(monkeypatch)

        await ua.run()

        loop_params_call = next(
            call
            for call in ua._debug_info_manager.add.call_args_list
            if call.args[0] == "loop_params"
        )
        payload = loop_params_call.args[1]
        assert isinstance(payload, list)
        assert len(payload) == 1

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__loop_params_entry__contains_loop_number_and_thinking_level(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that each entry in loop_params has the expected keys.
        Why this matters: Consumers read these keys by name; missing keys cause
        KeyErrors or require defensive coding across all consumers.
        Setup summary: Run one iteration; assert the single entry has both
        'loop_number' and 'thinking_level'.
        """
        ua = self._build_run_ua(monkeypatch)

        await ua.run()

        loop_params_call = next(
            call
            for call in ua._debug_info_manager.add.call_args_list
            if call.args[0] == "loop_params"
        )
        entry = loop_params_call.args[1][0]
        assert "loop_number" in entry
        assert "thinking_level" in entry

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__loop_debug_params__reset_on_each_run(self, monkeypatch) -> None:
        """
        Purpose: Verify that _loop_debug_params is cleared at the start of each
        run() call.
        Why this matters: Without a reset, consecutive run() calls on the same
        instance accumulate stale entries from previous runs, inflating the
        loop_params list.
        Setup summary: Run twice; assert _loop_debug_params has exactly one entry
        after the second run (not two).
        """
        ua = self._build_run_ua(monkeypatch)

        await ua.run()
        await ua.run()

        assert len(ua._loop_debug_params) == 1
