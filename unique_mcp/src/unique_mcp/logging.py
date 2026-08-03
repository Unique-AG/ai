"""Pino-JSON logging for Unique MCP servers (Loki label: pino-json)."""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from typing import Any, Literal

from opentelemetry import trace

_SKIP = ("/probe", "/health", "/metrics", "/ready")
_PINO_LEVEL = {
    logging.DEBUG: 20,
    logging.INFO: 30,
    logging.WARNING: 40,
    logging.ERROR: 50,
    logging.CRITICAL: 60,
}
_RESERVED = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message"
}


class _QuietAccess(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(p in msg for p in _SKIP)


def _trace_fields() -> dict[str, str | int]:
    ctx = trace.get_current_span().get_span_context()
    if not ctx.is_valid:
        return {}
    return {
        "trace_id": format(ctx.trace_id, "032x"),
        "span_id": format(ctx.span_id, "016x"),
        "trace_flags": int(ctx.trace_flags),
    }


def _err_payload(
    exc_info: tuple[type[BaseException], BaseException, Any],
) -> dict[str, str]:
    exc_type, exc, tb = exc_info
    return {
        "name": exc_type.__name__,
        "message": str(exc),
        "stack": "".join(traceback.format_exception(exc_type, exc, tb)),
    }


class _PinoJson(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": _PINO_LEVEL.get(record.levelno, 30),
            "time": int(record.created * 1000),
            "msg": record.getMessage(),
            "context": record.name,
            **_trace_fields(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info and not isinstance(payload.get("err"), dict):
            payload["err"] = _err_payload(record.exc_info)  # type: ignore[arg-type]
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(
    *,
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | str | None = None,
) -> None:
    resolved = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    if resolved not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        resolved = "INFO"

    root = logging.getLogger()
    root.setLevel(resolved)
    has_pino = any(
        isinstance(getattr(h, "formatter", None), _PinoJson) for h in root.handlers
    )
    if not has_pino:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(_PinoJson())
        root.addHandler(handler)
    for handler in root.handlers:
        handler.setLevel(resolved)

    quiet = _QuietAccess()
    for name in ("uvicorn.access", "uvicorn.asgi"):
        log = logging.getLogger(name)
        if not any(isinstance(f, _QuietAccess) for f in log.filters):
            log.addFilter(quiet)
