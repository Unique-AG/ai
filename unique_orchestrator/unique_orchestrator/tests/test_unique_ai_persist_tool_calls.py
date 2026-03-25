from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from unique_orchestrator.unique_ai import UniqueAI


def _make_unique_ai(monkeypatch) -> UniqueAI:
    """Create a minimal UniqueAI instance with all heavy dependencies mocked."""
    mock_message_step_logger_class = MagicMock()
    mock_service_module = MagicMock()
    mock_service_module.MessageStepLogger = mock_message_step_logger_class
    monkeypatch.setitem(
        sys.modules,
        "unique_toolkit.agentic.message_log_manager.service",
        mock_service_module,
    )

    from unique_orchestrator.unique_ai import UniqueAI

    dummy_event = MagicMock()
    dummy_event.payload.assistant_message.id = "assist_1"
    dummy_event.payload.user_message.text = "query"

    mock_config = MagicMock()
    mock_config.agent.prompt_config.user_metadata = []

    mock_chat_service = MagicMock()
    mock_chat_service.create_message_tools_async = AsyncMock()

    mock_history_manager = MagicMock()

    ua = UniqueAI(
        logger=MagicMock(),
        event=dummy_event,
        config=mock_config,
        chat_service=mock_chat_service,
        content_service=MagicMock(),
        debug_info_manager=MagicMock(),
        streaming_handler=MagicMock(),
        reference_manager=MagicMock(),
        thinking_manager=MagicMock(),
        tool_manager=MagicMock(),
        history_manager=mock_history_manager,
        evaluation_manager=MagicMock(),
        postprocessor_manager=MagicMock(),
        message_step_logger=MagicMock(),
        mcp_servers=[],
        loop_iteration_runner=MagicMock(),
    )

    return ua


class TestPersistToolCalls:
    """Test suite for UniqueAI._persist_tool_calls method."""

    @pytest.mark.asyncio
    @pytest.mark.ai
    async def test_persist_tool_calls__returns_early__when_no_records(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that _persist_tool_calls does nothing when the history manager yields no records.

        Why this matters: An early exit avoids an unnecessary DB round-trip when the
        agent did not use any tools in the current loop.

        Setup summary: history_manager.extract_message_tools returns []; assert
        create_message_tools_async is never called.
        """
        ua = _make_unique_ai(monkeypatch)
        ua._history_manager.extract_message_tools.return_value = []

        await ua._persist_tool_calls()

        ua._chat_service.create_message_tools_async.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.ai
    async def test_persist_tool_calls__persists_records__when_records_exist(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that _persist_tool_calls calls create_message_tools_async with the
        (potentially compacted) records when tool call records are present.

        Why this matters: Persistence is the primary side-effect of this method; records
        must reach the database so that tool call history can be reconstructed in future turns.

        Setup summary: history_manager.extract_message_tools returns two mock records;
        HistoryManager.compact_message_tools is stubbed to return them unchanged;
        assert create_message_tools_async is awaited with those records.
        """
        ua = _make_unique_ai(monkeypatch)
        record_a, record_b = MagicMock(), MagicMock()
        ua._history_manager.extract_message_tools.return_value = [record_a, record_b]
        ua._last_assistant_text = "some assistant text"

        with patch(
            "unique_orchestrator.unique_ai.HistoryManager.compact_message_tools",
            return_value=[record_a, record_b],
        ) as mock_compact:
            await ua._persist_tool_calls()

            mock_compact.assert_called_once_with(
                records=[record_a, record_b],
                assistant_text="some assistant text",
            )

        ua._chat_service.create_message_tools_async.assert_awaited_once_with(
            tool_calls=[record_a, record_b],
        )

    @pytest.mark.asyncio
    @pytest.mark.ai
    async def test_persist_tool_calls__logs_count__after_successful_persistence(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that an info log entry with the record count is emitted after
        a successful persistence call.

        Why this matters: Observability of how many records were written helps with
        debugging and monitoring tool call behaviour in production.

        Setup summary: Two records are returned by extract_message_tools; assert the
        logger's info method is called with a message that references the count (2).
        """
        ua = _make_unique_ai(monkeypatch)
        records = [MagicMock(), MagicMock()]
        ua._history_manager.extract_message_tools.return_value = records
        ua._last_assistant_text = None

        with patch(
            "unique_orchestrator.unique_ai.HistoryManager.compact_message_tools",
            return_value=records,
        ):
            await ua._persist_tool_calls()

        log_calls = [str(call) for call in ua._logger.info.call_args_list]
        assert any("2" in msg for msg in log_calls)

    @pytest.mark.asyncio
    @pytest.mark.ai
    async def test_persist_tool_calls__logs_error__when_db_raises(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that a DB error during persistence is caught, logged, and does
        not propagate to the caller.

        Why this matters: A failure to persist tool call records must not crash the
        agent loop; the assistant message should still be delivered to the user.

        Setup summary: create_message_tools_async raises RuntimeError; assert the
        logger's error method is called and the coroutine completes without raising.
        """
        ua = _make_unique_ai(monkeypatch)
        ua._history_manager.extract_message_tools.return_value = [MagicMock()]
        ua._chat_service.create_message_tools_async = AsyncMock(
            side_effect=RuntimeError("DB unavailable")
        )

        with patch(
            "unique_orchestrator.unique_ai.HistoryManager.compact_message_tools",
            return_value=[MagicMock()],
        ):
            await ua._persist_tool_calls()

        ua._logger.error.assert_called_once_with(
            "Failed to persist tool calls", exc_info=True
        )

    @pytest.mark.asyncio
    @pytest.mark.ai
    async def test_persist_tool_calls__passes_last_assistant_text_to_compact(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that the current value of _last_assistant_text is forwarded to
        compact_message_tools so that uncited sources are stripped before persistence.

        Why this matters: Compaction removes irrelevant web search results from the
        stored record, keeping the DB lean and reconstruction accurate.

        Setup summary: Set _last_assistant_text to a known string; capture the kwargs
        passed to compact_message_tools and assert assistant_text matches.
        """
        ua = _make_unique_ai(monkeypatch)
        ua._history_manager.extract_message_tools.return_value = [MagicMock()]
        ua._last_assistant_text = "Here is the answer [source3]."

        captured_kwargs: dict = {}

        def fake_compact(*, records, assistant_text):
            captured_kwargs["assistant_text"] = assistant_text
            return records

        with patch(
            "unique_orchestrator.unique_ai.HistoryManager.compact_message_tools",
            side_effect=fake_compact,
        ):
            await ua._persist_tool_calls()

        assert captured_kwargs["assistant_text"] == "Here is the answer [source3]."

    @pytest.mark.asyncio
    @pytest.mark.ai
    async def test_persist_tool_calls__none_last_assistant_text__still_persists(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify that _persist_tool_calls works correctly when _last_assistant_text
        is None (the initial default), skipping compaction transparently.

        Why this matters: On the very first turn or when the assistant produced no text,
        _last_assistant_text is None; the method must still persist the tool call records.

        Setup summary: _last_assistant_text is None; compact_message_tools returns records
        unmodified; assert create_message_tools_async is awaited with those records.
        """
        ua = _make_unique_ai(monkeypatch)
        record = MagicMock()
        ua._history_manager.extract_message_tools.return_value = [record]
        ua._last_assistant_text = None

        with patch(
            "unique_orchestrator.unique_ai.HistoryManager.compact_message_tools",
            return_value=[record],
        ):
            await ua._persist_tool_calls()

        ua._chat_service.create_message_tools_async.assert_awaited_once_with(
            tool_calls=[record],
        )
