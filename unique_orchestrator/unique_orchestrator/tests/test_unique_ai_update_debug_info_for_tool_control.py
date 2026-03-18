from unittest.mock import AsyncMock, MagicMock

import pytest


class TestPersistDebugInfo:
    """Test suite for UniqueAI._persist_debug_info and related methods."""

    @pytest.fixture
    def mock_unique_ai(self):
        """Create a minimal UniqueAI instance with mocked dependencies"""
        from unique_orchestrator.unique_ai import UniqueAI

        mock_logger = MagicMock()

        dummy_event = MagicMock()
        dummy_event.payload.assistant_message.id = "assist_1"
        dummy_event.payload.user_message.text = "query"
        dummy_event.payload.assistant_id = "assistant_123"
        dummy_event.payload.name = "TestAssistant"
        dummy_event.payload.user_metadata = {"key": "value"}
        dummy_event.payload.tool_parameters = {"param": "value"}

        mock_config = MagicMock()
        mock_config.agent.prompt_config.user_metadata = []

        mock_chat_service = MagicMock()
        mock_chat_service.update_debug_info_async = AsyncMock()
        mock_content_service = MagicMock()
        mock_debug_info_manager = MagicMock()
        mock_reference_manager = MagicMock()
        mock_thinking_manager = MagicMock()
        mock_tool_manager = MagicMock()
        mock_history_manager = MagicMock()
        mock_evaluation_manager = MagicMock()
        mock_postprocessor_manager = MagicMock()
        mock_streaming_handler = MagicMock()
        mock_message_step_logger = MagicMock()
        mock_loop_iteration_runner = MagicMock()

        ua = UniqueAI(
            logger=mock_logger,
            event=dummy_event,
            config=mock_config,
            chat_service=mock_chat_service,
            content_service=mock_content_service,
            debug_info_manager=mock_debug_info_manager,
            streaming_handler=mock_streaming_handler,
            reference_manager=mock_reference_manager,
            thinking_manager=mock_thinking_manager,
            tool_manager=mock_tool_manager,
            history_manager=mock_history_manager,
            evaluation_manager=mock_evaluation_manager,
            postprocessor_manager=mock_postprocessor_manager,
            message_step_logger=mock_message_step_logger,
            mcp_servers=[],
            loop_iteration_runner=mock_loop_iteration_runner,
        )

        return ua

    # ── _build_debug_info_event ──────────────────────────────────────

    @pytest.mark.ai
    def test_build_debug_info_event__includes_assistant_metadata(
        self, mock_unique_ai
    ) -> None:
        debug_info = {"tools": [{"name": "SearchTool", "info": {}}]}
        mock_unique_ai._debug_info_manager.get.return_value = debug_info

        result = mock_unique_ai._build_debug_info_event()

        assert result["assistant"] == {
            "id": "assistant_123",
            "name": "TestAssistant",
        }
        assert result["chosenModule"] == "TestAssistant"
        assert result["userMetadata"] == {"key": "value"}
        assert result["toolParameters"] == {"param": "value"}
        assert result["tools"] == debug_info["tools"]

    # ── _persist_debug_info ──────────────────────────────────────────

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_persist_debug_info__always_calls_update_debug_info(
        self, mock_unique_ai
    ) -> None:
        """Persist runs unconditionally (no tool-took-control guard)."""
        mock_unique_ai._tool_took_control = False
        debug_info = {"tools": [{"name": "SearchTool", "info": {}}]}
        mock_unique_ai._debug_info_manager.get.return_value = debug_info

        await mock_unique_ai._persist_debug_info()

        mock_unique_ai._chat_service.update_debug_info_async.assert_called_once()
        call_arg = mock_unique_ai._chat_service.update_debug_info_async.call_args
        assert call_arg.kwargs["debug_info"]["tools"] == debug_info["tools"]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_persist_debug_info__also_runs_when_tool_took_control(
        self, mock_unique_ai
    ) -> None:
        mock_unique_ai._tool_took_control = True
        debug_info = {"tools": [{"name": "SWOT", "info": {}}]}
        mock_unique_ai._debug_info_manager.get.return_value = debug_info

        await mock_unique_ai._persist_debug_info()

        mock_unique_ai._chat_service.update_debug_info_async.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_persist_debug_info__skips_deep_research(
        self, mock_unique_ai
    ) -> None:
        mock_unique_ai._tool_took_control = True
        mock_unique_ai._debug_info_manager.get.return_value = {
            "tools": [{"name": "DeepResearch"}]
        }

        await mock_unique_ai._persist_debug_info()

        mock_unique_ai._chat_service.update_debug_info_async.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_persist_debug_info__skips_deep_research_among_others(
        self, mock_unique_ai
    ) -> None:
        mock_unique_ai._debug_info_manager.get.return_value = {
            "tools": [{"name": "DeepResearch"}, {"name": "SearchTool"}]
        }

        await mock_unique_ai._persist_debug_info()

        mock_unique_ai._chat_service.update_debug_info_async.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_persist_debug_info__deep_research_check_is_case_sensitive(
        self, mock_unique_ai
    ) -> None:
        mock_unique_ai._debug_info_manager.get.return_value = {
            "tools": [{"name": "deepresearch"}, {"name": "DEEPRESEARCH"}]
        }

        await mock_unique_ai._persist_debug_info()

        mock_unique_ai._chat_service.update_debug_info_async.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_persist_debug_info__handles_none_user_metadata(
        self, mock_unique_ai
    ) -> None:
        mock_unique_ai._event.payload.user_metadata = None
        mock_unique_ai._debug_info_manager.get.return_value = {
            "tools": [{"name": "SearchTool"}]
        }

        await mock_unique_ai._persist_debug_info()

        call_arg = mock_unique_ai._chat_service.update_debug_info_async.call_args
        assert call_arg.kwargs["debug_info"]["userMetadata"] is None

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_persist_debug_info__handles_empty_tools(
        self, mock_unique_ai
    ) -> None:
        mock_unique_ai._debug_info_manager.get.return_value = {"tools": []}

        await mock_unique_ai._persist_debug_info()

        mock_unique_ai._chat_service.update_debug_info_async.assert_called_once()

    # ── _persist_debug_info_best_effort ──────────────────────────────

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_persist_debug_info_best_effort__swallows_errors(
        self, mock_unique_ai
    ) -> None:
        mock_unique_ai._debug_info_manager.get.return_value = {
            "tools": [{"name": "SearchTool"}]
        }
        mock_unique_ai._chat_service.update_debug_info_async = AsyncMock(
            side_effect=RuntimeError("API unavailable")
        )

        await mock_unique_ai._persist_debug_info_best_effort()

        mock_unique_ai._logger.debug.assert_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_persist_debug_info_best_effort__succeeds_normally(
        self, mock_unique_ai
    ) -> None:
        mock_unique_ai._debug_info_manager.get.return_value = {
            "tools": [{"name": "SearchTool"}]
        }

        await mock_unique_ai._persist_debug_info_best_effort()

        mock_unique_ai._chat_service.update_debug_info_async.assert_called_once()


class TestLogToolResults:
    """Test suite for UniqueAI._log_tool_results and _format_tool_result_summary."""

    @pytest.fixture
    def mock_unique_ai(self):
        from unique_orchestrator.unique_ai import UniqueAI

        mock_logger = MagicMock()
        dummy_event = MagicMock()
        dummy_event.payload.assistant_message.id = "assist_1"
        dummy_event.payload.user_message.text = "query"
        dummy_event.payload.assistant_id = "assistant_123"
        dummy_event.payload.name = "TestAssistant"
        dummy_event.payload.user_metadata = {}
        dummy_event.payload.tool_parameters = {}

        mock_config = MagicMock()
        mock_config.agent.prompt_config.user_metadata = []

        mock_message_step_logger = MagicMock()

        ua = UniqueAI(
            logger=mock_logger,
            event=dummy_event,
            config=mock_config,
            chat_service=MagicMock(),
            content_service=MagicMock(),
            debug_info_manager=MagicMock(),
            streaming_handler=MagicMock(),
            reference_manager=MagicMock(),
            thinking_manager=MagicMock(),
            tool_manager=MagicMock(),
            history_manager=MagicMock(),
            evaluation_manager=MagicMock(),
            postprocessor_manager=MagicMock(),
            message_step_logger=mock_message_step_logger,
            mcp_servers=[],
            loop_iteration_runner=MagicMock(),
        )

        return ua

    # ── _log_tool_results ────────────────────────────────────────────

    @pytest.mark.ai
    def test_log_tool_results__creates_entry_for_tool_with_debug_info(
        self, mock_unique_ai
    ) -> None:
        response = MagicMock()
        response.name = "todo_write"
        response.debug_info = {
            "state": {"total": 3, "completed": 1, "in_progress": 1, "pending": 1}
        }

        mock_unique_ai._log_tool_results([response])

        mock_unique_ai._message_step_logger.create_message_log_entry.assert_called_once()
        call_text = mock_unique_ai._message_step_logger.create_message_log_entry.call_args.kwargs[
            "text"
        ]
        assert "todo_write" in call_text
        assert "3 items" in call_text

    @pytest.mark.ai
    def test_log_tool_results__skips_tool_without_debug_info(
        self, mock_unique_ai
    ) -> None:
        response = MagicMock()
        response.name = "WebSearch"
        response.debug_info = None

        mock_unique_ai._log_tool_results([response])

        mock_unique_ai._message_step_logger.create_message_log_entry.assert_not_called()

    @pytest.mark.ai
    def test_log_tool_results__skips_empty_debug_info(self, mock_unique_ai) -> None:
        response = MagicMock()
        response.name = "WebSearch"
        response.debug_info = {}

        mock_unique_ai._log_tool_results([response])

        mock_unique_ai._message_step_logger.create_message_log_entry.assert_not_called()

    @pytest.mark.ai
    def test_log_tool_results__skips_deep_research(self, mock_unique_ai) -> None:
        response = MagicMock()
        response.name = "DeepResearch"
        response.debug_info = {"some": "data"}

        mock_unique_ai._log_tool_results([response])

        mock_unique_ai._message_step_logger.create_message_log_entry.assert_not_called()

    @pytest.mark.ai
    def test_log_tool_results__handles_multiple_responses(self, mock_unique_ai) -> None:
        r1 = MagicMock()
        r1.name = "todo_write"
        r1.debug_info = {
            "state": {"total": 2, "completed": 0, "in_progress": 1, "pending": 1}
        }

        r2 = MagicMock()
        r2.name = "WebSearch"
        r2.debug_info = None

        r3 = MagicMock()
        r3.name = "InternalSearch"
        r3.debug_info = {"query": "test", "hits": 5}

        mock_unique_ai._log_tool_results([r1, r2, r3])

        assert (
            mock_unique_ai._message_step_logger.create_message_log_entry.call_count == 2
        )

    # ── _format_tool_result_summary ──────────────────────────────────

    @pytest.mark.ai
    def test_format_todo_state_summary(self) -> None:
        from unique_orchestrator.unique_ai import UniqueAI

        result = UniqueAI._format_tool_result_summary(
            "todo_write",
            {"state": {"total": 5, "completed": 2, "in_progress": 1, "pending": 2}},
        )
        assert (
            result == "**todo_write** — 5 items (2 completed, 1 in_progress, 2 pending)"
        )

    @pytest.mark.ai
    def test_format_todo_state_summary_empty(self) -> None:
        from unique_orchestrator.unique_ai import UniqueAI

        result = UniqueAI._format_tool_result_summary(
            "todo_write",
            {"state": {"total": 0, "completed": 0, "in_progress": 0, "pending": 0}},
        )
        assert result == "**todo_write** — 0 items (empty)"

    @pytest.mark.ai
    def test_format_generic_debug_info(self) -> None:
        from unique_orchestrator.unique_ai import UniqueAI

        result = UniqueAI._format_tool_result_summary(
            "InternalSearch",
            {"query": "test query", "hits": 42},
        )
        assert result is not None
        assert "InternalSearch" in result
        assert "query" in result

    @pytest.mark.ai
    def test_format_skips_mcp_keys(self) -> None:
        from unique_orchestrator.unique_ai import UniqueAI

        result = UniqueAI._format_tool_result_summary(
            "MCPTool",
            {"mcp_server": "my-server", "mcp_tool": "my-tool"},
        )
        assert result is None

    @pytest.mark.ai
    def test_format_limits_to_three_keys(self) -> None:
        from unique_orchestrator.unique_ai import UniqueAI

        result = UniqueAI._format_tool_result_summary(
            "BigTool",
            {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5},
        )
        assert result is not None
        assert result.count(":") == 3
