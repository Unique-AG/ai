"""Tests for unique_mcp.logging helpers."""

from __future__ import annotations

import json
import logging
import sys

import pytest
from opentelemetry import context, trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

from unique_mcp.logging import _PinoJson, _QuietAccess, configure_logging


@pytest.mark.ai
@pytest.mark.unit
@pytest.mark.parametrize(
    ("message", "expected"),
    [
        # uvicorn
        ('127.0.0.1:1 - "GET /probe HTTP/1.1" 200', False),
        ('127.0.0.1:1 - "GET /probe/ HTTP/1.1" 200', False),
        ('127.0.0.1:1 - "GET /metrics HTTP/1.1" 200', False),
        ('127.0.0.1:1 - "GET /health HTTP/1.1" 200', False),
        ('127.0.0.1:1 - "GET /ready HTTP/1.1" 200', False),
        ('127.0.0.1:1 - "GET /mcp HTTP/1.1" 200', True),
        ('127.0.0.1:1 - "POST /mcp HTTP/1.1" 200', True),
        # combined / CLF-style (hypercorn and others)
        (
            '127.0.0.1 - - [03/Aug/2026:12:00:00 +0000] "GET /metrics HTTP/1.1" 200 12',
            False,
        ),
        (
            '127.0.0.1 - - [03/Aug/2026:12:00:00 +0000] "POST /mcp HTTP/1.1" 200 12',
            True,
        ),
        # bare METHOD path status
        ("GET /ready 200", False),
        ("POST /mcp 200", True),
        # Substring / query must not suppress real traffic (Bugbot MEDIUM).
        ('127.0.0.1:1 - "GET /mcp?next=/probe HTTP/1.1" 200', True),
        ('127.0.0.1:1 - "GET /api/healthcheck HTTP/1.1" 200', True),
        ('127.0.0.1:1 - "POST /tools/metrics-export HTTP/1.1" 200', True),
        ("not an access line at all", True),
    ],
)
def test_quiet_access__skips_probe_and_metrics(message: str, expected: bool) -> None:
    """
    Purpose: Verify access logs for exact ops paths are dropped, not substrings.
    Why this matters: Scrapes drown logs; substring skips hid attacker-controlled URLs.
    Setup summary: Filter sample ASGI access lines; assert keep/drop.
    """
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )
    assert _QuietAccess().filter(record) is expected


@pytest.mark.ai
@pytest.mark.unit
def test_pino_json__emits_level_time_msg() -> None:
    """
    Purpose: Verify JSON formatter matches pino-json field names.
    Why this matters: Alloy/Loki expect numeric level, time ms, msg, context.
    Setup summary: Format a LogRecord and parse the JSON payload.
    """
    record = logging.LogRecord(
        name="unique_mcp.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    record.company_id = "co-1"  # type: ignore[attr-defined]

    payload = json.loads(_PinoJson().format(record))

    assert payload["level"] == 30
    assert payload["msg"] == "hello world"
    assert payload["context"] == "unique_mcp.test"
    assert payload["company_id"] == "co-1"
    assert isinstance(payload["time"], int)


@pytest.mark.ai
@pytest.mark.unit
def test_pino_json__err_is_structured_object() -> None:
    """
    Purpose: Verify exceptions serialize like connectors TS err shape.
    Why this matters: Loki Explore expects err.name / message / stack, not a string.
    Setup summary: Format a LogRecord with exc_info from a RuntimeError.
    """
    try:
        raise RuntimeError("nope")
    except RuntimeError:
        record = logging.LogRecord(
            name="unique_mcp.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="operation failed",
            args=(),
            exc_info=sys.exc_info(),
        )

    payload = json.loads(_PinoJson().format(record))

    assert payload["err"]["name"] == "RuntimeError"
    assert payload["err"]["message"] == "nope"
    assert "RuntimeError: nope" in payload["err"]["stack"]


@pytest.mark.ai
@pytest.mark.unit
def test_pino_json__includes_trace_fields_from_active_span() -> None:
    """
    Purpose: Verify trace_id/span_id/trace_flags come from the active OTel span.
    Why this matters: QA Loki correlates MCP logs the same way as TS MCPs.
    Setup summary: Attach a NonRecordingSpan and format a record.
    """
    span_ctx = SpanContext(
        trace_id=0xA048E90ACEF882E46FDFE481C06237C1,
        span_id=0x745E84549F5E6FE3,
        is_remote=False,
        trace_flags=TraceFlags(0x01),
    )
    token = context.attach(trace.set_span_in_context(NonRecordingSpan(span_ctx)))
    try:
        record = logging.LogRecord(
            name="unique_mcp.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="traced",
            args=(),
            exc_info=None,
        )
        payload = json.loads(_PinoJson().format(record))
    finally:
        context.detach(token)

    assert payload["trace_id"] == "a048e90acef882e46fdfe481c06237c1"
    assert payload["span_id"] == "745e84549f5e6fe3"
    assert payload["trace_flags"] == 1


@pytest.mark.ai
@pytest.mark.unit
def test_configure_logging__installs_access_filter_idempotently() -> None:
    """
    Purpose: Verify configure_logging attaches a single quiet-access filter.
    Why this matters: Re-configure must not stack duplicate filters.
    Setup summary: Clear filters on common ASGI access loggers, configure twice.
    """
    for name in ("uvicorn.access", "hypercorn.access", "granian.access"):
        logging.getLogger(name).filters.clear()

    configure_logging(level="INFO")
    configure_logging(level="INFO")

    for name in ("uvicorn.access", "hypercorn.access", "granian.access"):
        assert (
            sum(isinstance(f, _QuietAccess) for f in logging.getLogger(name).filters)
            == 1
        )
