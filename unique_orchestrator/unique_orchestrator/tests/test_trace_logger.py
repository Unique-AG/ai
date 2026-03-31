"""Tests for the TraceLogger utility."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from unique_orchestrator.trace_logger import TraceLogger, _serialize, _strip_chunks


class TestSerialize:
    def test_none(self) -> None:
        assert _serialize(None) is None

    def test_dict(self) -> None:
        result = _serialize({"key": "value"})
        assert result == {"key": "value"}

    def test_dict_with_nested_model(self) -> None:
        model = MagicMock()
        model.model_dump.return_value = {"field": "val"}
        result = _serialize({"outer": model})
        assert result == {"outer": {"field": "val"}}

    def test_dict_strips_content_chunks(self) -> None:
        result = _serialize({"key": "value", "content_chunks": [1, 2]})
        assert result == {"key": "value"}

    def test_list(self) -> None:
        result = _serialize([1, 2, 3])
        assert result == ["1", "2", "3"]

    def test_pydantic_model(self) -> None:
        model = MagicMock()
        model.model_dump.return_value = {"field": "val", "content_chunks": [1, 2]}
        result = _serialize(model)
        assert result == {"field": "val"}

    def test_plain_value(self) -> None:
        assert _serialize(42) == "42"


class TestStripChunks:
    def test_removes_content_chunks(self) -> None:
        data = {"a": 1, "content_chunks": [1, 2, 3], "b": 2}
        assert _strip_chunks(data) == {"a": 1, "b": 2}

    def test_removes_camel_case_variant(self) -> None:
        data = {"a": 1, "contentChunks": [1, 2, 3]}
        assert _strip_chunks(data) == {"a": 1}

    def test_recursive_removal(self) -> None:
        data = {
            "outer": {
                "inner": "keep",
                "content_chunks": [1],
            }
        }
        result = _strip_chunks(data)
        assert result == {"outer": {"inner": "keep"}}

    def test_list_recursive(self) -> None:
        data = [{"content_chunks": [1], "keep": True}]
        result = _strip_chunks(data)
        assert result == [{"keep": True}]

    def test_passthrough_non_dict(self) -> None:
        assert _strip_chunks(42) == 42
        assert _strip_chunks("string") == "string"


class TestTraceLoggerDisabled:
    def test_disabled_when_no_env_and_non_dev(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            tl = TraceLogger()
            assert tl.enabled is False

    def test_noop_when_disabled(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            tl = TraceLogger()
            tl.log_llm_call(0, messages=[], response={})
            tl.log_tool_execution(0, tool_calls=[], tool_responses=[])
            tl.write_session_summary()


class TestTraceLoggerEnabled:
    def test_enabled_via_env_var(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"UNIQUE_AI_TRACE_DIR": str(tmp_path)}):
            tl = TraceLogger(chat_id="test-chat")
            assert tl.enabled is True
            assert tl._session_dir is not None
            assert "test-chat" in str(tl._session_dir)

    def test_dev_mode_auto_enables(self) -> None:
        with patch.dict(os.environ, {"ENV": "local"}, clear=True):
            tl = TraceLogger()
            assert tl.enabled is True

    def test_writes_llm_trace(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"UNIQUE_AI_TRACE_DIR": str(tmp_path)}):
            tl = TraceLogger()
            tl.log_llm_call(
                0,
                messages=[{"role": "user", "content": "hello"}],
                response={"text": "hi"},
                model="gpt-5.4",
            )

            files = list(tl._session_dir.glob("iter-*-llm.json"))  # type: ignore[union-attr]
            assert len(files) == 1
            data = json.loads(files[0].read_text())
            assert data["iteration"] == 0
            assert data["model"] == "gpt-5.4"

    def test_writes_tool_trace_with_system_reminder(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"UNIQUE_AI_TRACE_DIR": str(tmp_path)}):
            tl = TraceLogger()

            resp = MagicMock()
            resp.name = "todo_write"
            resp.system_reminder = "Keep going"
            resp.debug_info = {
                "state": {"total": 3, "completed": 1, "in_progress": 1, "pending": 1}
            }

            tl.log_tool_execution(0, tool_calls=[], tool_responses=[resp])

            files = list(tl._session_dir.glob("iter-*-tools.json"))  # type: ignore[union-attr]
            assert len(files) == 1
            data = json.loads(files[0].read_text())
            assert data["system_reminders"][0]["tool"] == "todo_write"
            assert data["tool_debug_info"]["todo_write"]["state"]["total"] == 3

    def test_writes_session_summary(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"UNIQUE_AI_TRACE_DIR": str(tmp_path)}):
            tl = TraceLogger()
            tl._tools_used = ["search", "todo_write", "search"]
            tl._iteration_count = 3
            tl._model = "gpt-5.4"

            tl.write_session_summary()

            summary_file = tl._session_dir / "session-summary.json"  # type: ignore[operator]
            assert summary_file.exists()
            data = json.loads(summary_file.read_text())
            assert data["total_iterations"] == 3
            assert data["model"] == "gpt-5.4"
            assert set(data["tools_used"]) == {"search", "todo_write"}

    def test_tool_state_progression_tracking(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"UNIQUE_AI_TRACE_DIR": str(tmp_path)}):
            tl = TraceLogger()

            resp1 = MagicMock()
            resp1.name = "todo_write"
            resp1.system_reminder = ""
            resp1.debug_info = {
                "state": {"total": 3, "completed": 0, "in_progress": 1, "pending": 2}
            }
            tl.log_tool_execution(0, tool_calls=[], tool_responses=[resp1])

            resp2 = MagicMock()
            resp2.name = "todo_write"
            resp2.system_reminder = ""
            resp2.debug_info = {
                "state": {"total": 3, "completed": 2, "in_progress": 1, "pending": 0}
            }
            tl.log_tool_execution(1, tool_calls=[], tool_responses=[resp2])

            assert "todo_write" in tl._tool_state_progression
            progression = tl._tool_state_progression["todo_write"]
            assert len(progression) == 2
            assert progression[0]["pending"] == 2
            assert progression[1]["completed"] == 2

    def test_tool_state_progression_multiple_tools(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"UNIQUE_AI_TRACE_DIR": str(tmp_path)}):
            tl = TraceLogger()

            resp_todo = MagicMock()
            resp_todo.name = "todo_write"
            resp_todo.system_reminder = ""
            resp_todo.debug_info = {"state": {"total": 2, "completed": 1}}

            resp_other = MagicMock()
            resp_other.name = "some_tool"
            resp_other.system_reminder = None
            resp_other.debug_info = {"state": {"processed": 5, "errors": 0}}

            tl.log_tool_execution(
                0, tool_calls=[], tool_responses=[resp_todo, resp_other]
            )

            assert "todo_write" in tl._tool_state_progression
            assert "some_tool" in tl._tool_state_progression
            assert tl._tool_state_progression["some_tool"][0]["processed"] == 5
