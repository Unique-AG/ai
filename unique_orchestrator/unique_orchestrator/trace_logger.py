"""Lightweight trace logger for debugging agent message flow.

Enabled by setting ``UNIQUE_AI_TRACE_DIR`` (e.g. ``/tmp/unique-ai-traces``).
When active, each agent run gets a timestamped session directory and each
loop iteration writes a JSON file containing the messages sent to the LLM
and the response received -- excluding bulky content chunks.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from logging import getLogger
from pathlib import Path
from typing import Any

logger = getLogger(__name__)

_TRACE_DIR_ENV = "UNIQUE_AI_TRACE_DIR"


class TraceLogger:
    """Writes per-iteration JSON trace files when tracing is enabled."""

    def __init__(self, chat_id: str | None = None) -> None:
        trace_root = os.environ.get(_TRACE_DIR_ENV)
        if not trace_root:
            self._session_dir: Path | None = None
            return

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        suffix = f"-{chat_id}" if chat_id else ""
        self._session_dir = Path(trace_root) / f"{ts}{suffix}"
        self._session_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Trace logging enabled → %s", self._session_dir)

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
        """Log tool calls and their responses."""
        if not self._session_dir:
            return

        payload: dict[str, Any] = {
            "iteration": iteration,
            "phase": "tools",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_calls": _serialize(tool_calls),
            "tool_responses": _serialize(tool_responses),
        }

        self._write(f"iter-{iteration:03d}-tools.json", payload)

    def _write(self, filename: str, payload: dict[str, Any]) -> None:
        assert self._session_dir is not None
        path = self._session_dir / filename
        try:
            path.write_text(
                json.dumps(payload, indent=2, default=str), encoding="utf-8"
            )
        except Exception:
            logger.warning("Failed to write trace file %s", path, exc_info=True)


def _serialize(obj: Any) -> Any:
    """Best-effort serialization that strips content_chunks."""
    if hasattr(obj, "model_dump"):
        data = obj.model_dump(mode="json")
    elif hasattr(obj, "dict"):
        data = obj.dict()
    elif isinstance(obj, list):
        return [_serialize(item) for item in obj]
    elif isinstance(obj, dict):
        data = obj
    else:
        return str(obj)

    if isinstance(data, dict):
        data.pop("content_chunks", None)
        data.pop("contentChunks", None)
    return data
