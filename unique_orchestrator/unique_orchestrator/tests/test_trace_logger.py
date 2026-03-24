"""Tests for the TraceLogger."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from unique_orchestrator.trace_logger import TraceLogger, _serialize, _strip_chunks


class TestSerialize:
    """Tests for _serialize helper."""

    def test_none(self) -> None:
        assert _serialize(None) is None

    def test_dict_strips_content_chunks(self) -> None:
        data = {"a": 1, "content_chunks": [1, 2], "contentChunks": [3, 4]}
        result = _serialize(data)
        assert result == {"a": 1}

    def test_nested_dict_strips_recursively(self) -> None:
        data = {"outer": {"inner": 1, "content_chunks": ["x"]}}
        result = _serialize(data)
        assert result == {"outer": {"inner": 1}}

    def test_list_of_dicts(self) -> None:
        data = [{"a": 1, "content_chunks": []}, {"b": 2}]
        result = _serialize(data)
        assert result == [{"a": 1}, {"b": 2}]

    def test_pydantic_model(self) -> None:
        mock_obj = MagicMock()
        mock_obj.model_dump.return_value = {"key": "val", "contentChunks": []}
        result = _serialize(mock_obj)
        assert result == {"key": "val"}

    def test_plain_string(self) -> None:
        assert _serialize("hello") == "hello"

    def test_int(self) -> None:
        assert _serialize(42) == "42"


class TestStripChunks:
    """Tests for _strip_chunks helper."""

    def test_flat_dict(self) -> None:
        assert _strip_chunks({"a": 1, "content_chunks": []}) == {"a": 1}

    def test_nested(self) -> None:
        data = {"a": {"contentChunks": [], "b": 2}, "content_chunks": []}
        assert _strip_chunks(data) == {"a": {"b": 2}}

    def test_list_in_dict(self) -> None:
        data = {"items": [{"content_chunks": [], "x": 1}]}
        assert _strip_chunks(data) == {"items": [{"x": 1}]}

    def test_passthrough_non_dict(self) -> None:
        assert _strip_chunks("hello") == "hello"
        assert _strip_chunks(42) == 42


class TestTraceLoggerDisabled:
    """Tests when tracing is disabled (no env var set)."""

    def test_disabled_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            tl = TraceLogger(chat_id="test")
            assert not tl.enabled

    def test_log_llm_call_noop(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            tl = TraceLogger()
            tl.log_llm_call(0, messages=[], response="ok")

    def test_log_tool_execution_noop(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            tl = TraceLogger()
            tl.log_tool_execution(0, tool_calls=[], tool_responses=[])

    def test_write_session_summary_noop(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            tl = TraceLogger()
            tl.write_session_summary()


class TestTraceLoggerEnabled:
    """Tests when tracing is enabled via env var."""

    @pytest.fixture()
    def trace_dir(self, tmp_path: Path) -> Path:
        return tmp_path / "traces"

    @pytest.fixture()
    def trace_logger(self, trace_dir: Path) -> TraceLogger:
        with patch.dict(os.environ, {"UNIQUE_AI_TRACE_DIR": str(trace_dir)}):
            return TraceLogger(chat_id="test-chat")

    def test_enabled(self, trace_logger: TraceLogger) -> None:
        assert trace_logger.enabled

    def test_session_dir_created(
        self, trace_logger: TraceLogger, trace_dir: Path
    ) -> None:
        sessions = list(trace_dir.iterdir())
        assert len(sessions) == 1
        assert "test-chat" in sessions[0].name

    def test_log_llm_call_writes_file(self, trace_logger: TraceLogger) -> None:
        trace_logger.log_llm_call(
            0,
            messages=[{"role": "user", "content": "hi"}],
            response={"choices": []},
            model="gpt-4o",
        )
        files = list(trace_logger._session_dir.glob("iter-000-llm.json"))
        assert len(files) == 1

        data = json.loads(files[0].read_text())
        assert data["iteration"] == 0
        assert data["phase"] == "llm"
        assert data["model"] == "gpt-4o"
        assert data["messages"] == [{"role": "user", "content": "hi"}]

    def test_log_tool_execution_extracts_system_reminder(
        self, trace_logger: TraceLogger
    ) -> None:
        mock_response = MagicMock()
        mock_response.name = "todo_write"
        mock_response.system_reminder = "EXECUTION PHASE"
        mock_response.debug_info = {
            "state": {"total": 3, "completed": 1, "in_progress": 1, "pending": 1}
        }

        trace_logger.log_tool_execution(
            1,
            tool_calls=[{"name": "todo_write"}],
            tool_responses=[mock_response],
        )

        files = list(trace_logger._session_dir.glob("iter-001-tools.json"))
        assert len(files) == 1

        data = json.loads(files[0].read_text())
        assert data["system_reminders"] == [
            {"tool": "todo_write", "reminder": "EXECUTION PHASE"}
        ]
        assert data["todo_state"]["total"] == 3

    def test_log_tool_execution_without_reminder(
        self, trace_logger: TraceLogger
    ) -> None:
        mock_response = MagicMock()
        mock_response.name = "search"
        mock_response.system_reminder = None
        mock_response.debug_info = None

        trace_logger.log_tool_execution(
            0, tool_calls=[], tool_responses=[mock_response]
        )

        files = list(trace_logger._session_dir.glob("iter-000-tools.json"))
        data = json.loads(files[0].read_text())
        assert "system_reminders" not in data
        assert "todo_state" not in data

    def test_write_session_summary(self, trace_logger: TraceLogger) -> None:
        trace_logger.log_llm_call(0, messages=[], response="ok", model="gpt-4o")

        mock_resp = MagicMock()
        mock_resp.name = "todo_write"
        mock_resp.system_reminder = "reminder"
        mock_resp.debug_info = {
            "state": {"total": 2, "completed": 0, "in_progress": 1, "pending": 1}
        }
        trace_logger.log_tool_execution(0, tool_calls=[], tool_responses=[mock_resp])

        trace_logger.write_session_summary()

        files = list(trace_logger._session_dir.glob("session-summary.json"))
        assert len(files) == 1

        data = json.loads(files[0].read_text())
        assert data["total_iterations"] == 1
        assert data["model"] == "gpt-4o"
        assert "todo_write" in data["tools_used"]
        assert len(data["todo_progression"]) == 1
        assert data["total_time_s"] >= 0


class TestTraceLoggerDevMode:
    """Tests for dev-mode auto-enable behavior."""

    def test_dev_mode_enables_tracing(self, tmp_path: Path) -> None:
        with patch.dict(
            os.environ,
            {"ENV": "local", "UNIQUE_AI_TRACE_DIR": ""},
            clear=False,
        ):
            tl = TraceLogger(chat_id="dev-test")
            assert tl.enabled

    def test_non_dev_mode_disabled(self) -> None:
        with patch.dict(
            os.environ,
            {"ENV": "production"},
            clear=True,
        ):
            tl = TraceLogger()
            assert not tl.enabled
