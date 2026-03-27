"""Tests for debug_info persistence and tool result logging in UniqueAI.

Covers:
- _persist_debug_info always runs (not gated by tool-took-control)
- _persist_debug_info skips DeepResearch
- _persist_debug_info_best_effort swallows errors
- _build_debug_info_event includes assistant metadata
- _log_tool_results creates Steps entries for tools with debug_info
- _format_tool_result_summary formats todo state and generic debug info
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_unique_ai() -> MagicMock:
    """Create a mock UniqueAI instance with the methods under test."""
    from unique_orchestrator.unique_ai import UniqueAI

    ai = MagicMock(spec=UniqueAI)

    ai._debug_info_manager = MagicMock()
    ai._chat_service = MagicMock()
    ai._chat_service.update_debug_info_async = AsyncMock()
    ai._chat_service.get_debug_info_async = AsyncMock(return_value={})
    ai._event = MagicMock()
    ai._event.payload.assistant_id = "asst-1"
    ai._event.payload.name = "test-assistant"
    ai._event.payload.user_metadata = {"key": "value"}
    ai._event.payload.tool_parameters = {}
    ai._message_step_logger = MagicMock()
    ai._logger = MagicMock()

    ai._build_debug_info_event = UniqueAI._build_debug_info_event.__get__(ai)
    ai._persist_debug_info = UniqueAI._persist_debug_info.__get__(ai)
    ai._persist_debug_info_best_effort = (
        UniqueAI._persist_debug_info_best_effort.__get__(ai)
    )
    ai._log_tool_results = UniqueAI._log_tool_results.__get__(ai)
    ai._format_tool_result_summary = UniqueAI._format_tool_result_summary

    return ai


class TestBuildDebugInfoEvent:
    @pytest.mark.ai
    def test_includes_assistant_metadata(self) -> None:
        ai = _make_unique_ai()
        ai._debug_info_manager.get.return_value = {"tools": []}

        result = ai._build_debug_info_event()

        assert result["assistant"]["id"] == "asst-1"
        assert result["assistant"]["name"] == "test-assistant"
        assert result["chosenModule"] == "test-assistant"


class TestPersistDebugInfo:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_persists_when_no_deep_research(self) -> None:
        ai = _make_unique_ai()
        ai._debug_info_manager.get.return_value = {"tools": [{"name": "todo_write"}]}

        await ai._persist_debug_info()

        ai._chat_service.update_debug_info_async.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_skips_deep_research(self) -> None:
        ai = _make_unique_ai()
        ai._debug_info_manager.get.return_value = {"tools": [{"name": "DeepResearch"}]}

        await ai._persist_debug_info()

        ai._chat_service.update_debug_info_async.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_best_effort_swallows_errors(self) -> None:
        ai = _make_unique_ai()
        ai._debug_info_manager.get.return_value = {"tools": []}
        ai._chat_service.update_debug_info_async = AsyncMock(
            side_effect=Exception("Network error")
        )

        await ai._persist_debug_info_best_effort()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_handles_empty_debug_info(self) -> None:
        ai = _make_unique_ai()
        ai._debug_info_manager.get.return_value = {}

        await ai._persist_debug_info()

        ai._chat_service.update_debug_info_async.assert_called_once()


class TestLogToolResults:
    @pytest.mark.ai
    def test_creates_step_entry_for_todo_write(self) -> None:
        ai = _make_unique_ai()

        response = MagicMock()
        response.name = "todo_write"
        response.debug_info = {
            "state": {"total": 3, "completed": 1, "in_progress": 1, "pending": 1}
        }

        ai._log_tool_results([response])

        ai._message_step_logger.create_message_log_entry.assert_called_once()
        call_text = ai._message_step_logger.create_message_log_entry.call_args[1][
            "text"
        ]
        assert "todo_write" in call_text
        assert "3 items" in call_text

    @pytest.mark.ai
    def test_skips_deep_research(self) -> None:
        ai = _make_unique_ai()

        response = MagicMock()
        response.name = "DeepResearch"
        response.debug_info = {"some": "data"}

        ai._log_tool_results([response])

        ai._message_step_logger.create_message_log_entry.assert_not_called()

    @pytest.mark.ai
    def test_skips_tools_without_debug_info(self) -> None:
        ai = _make_unique_ai()

        response = MagicMock()
        response.name = "search"
        response.debug_info = None

        ai._log_tool_results([response])

        ai._message_step_logger.create_message_log_entry.assert_not_called()

    @pytest.mark.ai
    def test_generic_tool_with_debug_info(self) -> None:
        ai = _make_unique_ai()

        response = MagicMock()
        response.name = "custom_tool"
        response.debug_info = {"some": "data"}

        ai._log_tool_results([response])

        ai._message_step_logger.create_message_log_entry.assert_called_once()
        call_text = ai._message_step_logger.create_message_log_entry.call_args[1][
            "text"
        ]
        assert "custom_tool" in call_text


class TestFormatToolResultSummary:
    @pytest.mark.ai
    def test_todo_write_format(self) -> None:
        from unique_orchestrator.unique_ai import UniqueAI

        result = UniqueAI._format_tool_result_summary(
            "todo_write",
            {
                "state": {
                    "total": 5,
                    "completed": 2,
                    "in_progress": 1,
                    "pending": 2,
                }
            },
        )
        assert result is not None
        assert "5 items" in result
        assert "2 completed" in result
        assert "1 in_progress" in result
        assert "2 pending" in result

    @pytest.mark.ai
    def test_generic_tool_format(self) -> None:
        from unique_orchestrator.unique_ai import UniqueAI

        result = UniqueAI._format_tool_result_summary("other_tool", {"key": "value"})
        assert result is not None
        assert "other_tool" in result

    @pytest.mark.ai
    def test_todo_write_all_completed(self) -> None:
        from unique_orchestrator.unique_ai import UniqueAI

        result = UniqueAI._format_tool_result_summary(
            "todo_write",
            {"state": {"total": 3, "completed": 3, "in_progress": 0, "pending": 0}},
        )
        assert result is not None
        assert "3 completed" in result
        assert "pending" not in result
