"""Lightweight trace logger for debugging agent message flow.

Enabled by setting ``UNIQUE_AI_TRACE_DIR`` (e.g. ``/tmp/unique-ai-traces``).
When active, each agent run gets a timestamped session directory and each
loop iteration writes JSON files containing:

- ``iter-NNN-llm.json``: messages sent to the LLM and its response
- ``iter-NNN-tools.json``: tool calls, tool responses, system_reminders,
  and todo state snapshots
- ``session-summary.json``: written at end-of-run with iteration count,
  tools used, todo progression, timing, and model
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from logging import getLogger
from pathlib import Path
from typing import Any

logger = getLogger(__name__)

_TRACE_DIR_ENV = "UNIQUE_AI_TRACE_DIR"
_DEV_DEFAULT_DIR = "/tmp/unique-ai-traces"


def _is_dev_mode() -> bool:
    return os.environ.get("ENV", "").lower() in ("local", "dev", "development")


class TraceLogger:
    """Writes per-iteration JSON trace files when tracing is enabled."""

    def __init__(self, chat_id: str | None = None) -> None:
        trace_root = os.environ.get(_TRACE_DIR_ENV)
        if not trace_root and _is_dev_mode():
            trace_root = _DEV_DEFAULT_DIR

        if not trace_root:
            self._session_dir: Path | None = None
            return

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        suffix = f"-{chat_id}" if chat_id else ""
        self._session_dir = Path(trace_root) / f"{ts}{suffix}"
        self._session_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Trace logging enabled → %s", self._session_dir)

        self._run_start = time.perf_counter()
        self._iteration_count = 0
        self._tools_used: list[str] = []
        self._todo_progression: list[dict[str, int]] = []
        self._model: str | None = None

    @property
    def enabled(self) -> bool:
        return self._session_dir is not None

    def log_llm_call(
        self,
        iteration: int,
        *,
        messages: Any,
        response: Any,
        model: str | None = None,
    ) -> None:
        """Log the messages sent to the LLM and its response."""
        if not self._session_dir:
            return

        self._iteration_count = max(self._iteration_count, iteration + 1)
        if model:
            self._model = model

        payload: dict[str, Any] = {
            "iteration": iteration,
            "phase": "llm",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if model:
            payload["model"] = model
        payload["messages"] = _serialize(messages)
        payload["response"] = _serialize(response)

        self._write(f"iter-{iteration:03d}-llm.json", payload)

    def log_tool_execution(
        self,
        iteration: int,
        *,
        tool_calls: list[Any],
        tool_responses: list[Any],
    ) -> None:
        """Log tool calls and their responses, extracting system_reminders and todo state."""
        if not self._session_dir:
            return

        system_reminders: list[dict[str, str]] = []
        todo_state: dict[str, Any] | None = None

        for resp in tool_responses:
            name = getattr(resp, "name", None) or ""
            self._tools_used.append(name)

            reminder = getattr(resp, "system_reminder", None)
            if reminder:
                system_reminders.append({"tool": name, "reminder": reminder})

            debug = getattr(resp, "debug_info", None)
            if debug and isinstance(debug, dict) and "state" in debug:
                todo_state = debug["state"]

        if todo_state:
            snapshot = {
                k: todo_state.get(k, 0)
                for k in ("total", "completed", "in_progress", "pending")
            }
            self._todo_progression.append({"iteration": iteration, **snapshot})

        payload: dict[str, Any] = {
            "iteration": iteration,
            "phase": "tools",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_calls": _serialize(tool_calls),
            "tool_responses": _serialize(tool_responses),
        }

        if system_reminders:
            payload["system_reminders"] = system_reminders
        if todo_state:
            payload["todo_state"] = todo_state

        self._write(f"iter-{iteration:03d}-tools.json", payload)

    def write_session_summary(self) -> None:
        """Write a session summary file at end of run."""
        if not self._session_dir:
            return

        unique_tools = sorted(set(self._tools_used))
        elapsed = round(time.perf_counter() - self._run_start, 3)

        summary: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_iterations": self._iteration_count,
            "total_time_s": elapsed,
            "tools_used": unique_tools,
            "tool_call_count": len(self._tools_used),
        }
        if self._model:
            summary["model"] = self._model
        if self._todo_progression:
            summary["todo_progression"] = self._todo_progression

        self._write("session-summary.json", summary)

    def _write(self, filename: str, payload: dict[str, Any]) -> None:
        if self._session_dir is None:
            return
        path = self._session_dir / filename
        try:
            path.write_text(
                json.dumps(payload, indent=2, default=str), encoding="utf-8"
            )
        except Exception:
            logger.warning("Failed to write trace file %s", path, exc_info=True)


def _serialize(obj: Any) -> Any:
    """Best-effort serialization that strips content_chunks recursively."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        data = obj.model_dump(mode="json")
        return _strip_chunks(data)
    if hasattr(obj, "dict"):
        data = obj.dict()
        return _strip_chunks(data)
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return _strip_chunks(obj)
    return str(obj)


def _strip_chunks(data: Any) -> Any:
    """Recursively remove content_chunks/contentChunks from dicts."""
    if isinstance(data, dict):
        return {
            k: _strip_chunks(v)
            for k, v in data.items()
            if k not in ("content_chunks", "contentChunks")
        }
    if isinstance(data, list):
        return [_strip_chunks(item) for item in data]
    return data
