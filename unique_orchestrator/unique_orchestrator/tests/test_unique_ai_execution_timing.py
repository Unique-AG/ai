import time
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestFinalizeLoopTiming:
    """Test suite for UniqueAI._finalize_loop_timing and execution timing tracking"""

    @pytest.fixture
    def mock_unique_ai(self):
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

    @pytest.mark.ai
    def test_init_creates_empty_execution_times_list(self, mock_unique_ai) -> None:
        assert mock_unique_ai._execution_times == []

    @pytest.mark.ai
    def test_init_creates_empty_current_loop_timing_dict(self, mock_unique_ai) -> None:
        assert mock_unique_ai._current_loop_timing == {}

    @pytest.mark.ai
    def test_finalize_loop_timing_adds_total_loop_time(self, mock_unique_ai) -> None:
        mock_unique_ai._current_loop_timing = {
            "iteration": 1,
            "planning_or_streaming": 0.5,
        }

        loop_start = time.perf_counter() - 1.0
        mock_unique_ai._finalize_loop_timing(loop_start)

        assert "total_loop_time" in mock_unique_ai._current_loop_timing
        assert mock_unique_ai._current_loop_timing["total_loop_time"] >= 1.0

    @pytest.mark.ai
    def test_finalize_loop_timing_appends_to_execution_times(
        self, mock_unique_ai
    ) -> None:
        mock_unique_ai._current_loop_timing = {
            "iteration": 1,
            "planning_or_streaming": 0.5,
        }

        loop_start = time.perf_counter()
        mock_unique_ai._finalize_loop_timing(loop_start)

        assert len(mock_unique_ai._execution_times) == 1
        assert mock_unique_ai._execution_times[0] is mock_unique_ai._current_loop_timing

    @pytest.mark.ai
    def test_finalize_loop_timing_called_multiple_times_accumulates(
        self, mock_unique_ai
    ) -> None:
        timing_1 = {"iteration": 1, "planning_or_streaming": 0.3}
        mock_unique_ai._current_loop_timing = timing_1
        mock_unique_ai._finalize_loop_timing(time.perf_counter())

        timing_2 = {"iteration": 2, "planning_or_streaming": 0.7}
        mock_unique_ai._current_loop_timing = timing_2
        mock_unique_ai._finalize_loop_timing(time.perf_counter())

        assert len(mock_unique_ai._execution_times) == 2
        assert mock_unique_ai._execution_times[0]["iteration"] == 1
        assert mock_unique_ai._execution_times[1]["iteration"] == 2

    @pytest.mark.ai
    def test_finalize_loop_timing_rounds_to_three_decimals(
        self, mock_unique_ai
    ) -> None:
        mock_unique_ai._current_loop_timing = {"iteration": 1}

        loop_start = time.perf_counter()
        mock_unique_ai._finalize_loop_timing(loop_start)

        total = mock_unique_ai._current_loop_timing["total_loop_time"]
        parts = str(total).split(".")
        if len(parts) == 2:
            assert len(parts[1]) <= 3

    @pytest.mark.ai
    def test_finalize_loop_timing_preserves_existing_keys(self, mock_unique_ai) -> None:
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
