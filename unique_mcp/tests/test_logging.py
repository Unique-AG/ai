"""Tests for unique_mcp.logging helpers."""

from __future__ import annotations

import json
import logging

import pytest

from unique_mcp.logging import _PinoJson, _QuietAccess, configure_logging


@pytest.mark.ai
@pytest.mark.unit
@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ('127.0.0.1:1 - "GET /probe HTTP/1.1" 200', False),
        ('127.0.0.1:1 - "GET /metrics HTTP/1.1" 200', False),
        ('127.0.0.1:1 - "GET /health HTTP/1.1" 200', False),
        ('127.0.0.1:1 - "GET /mcp HTTP/1.1" 200', True),
        ('127.0.0.1:1 - "POST /mcp HTTP/1.1" 200', True),
    ],
)
def test_quiet_access__skips_probe_and_metrics(message: str, expected: bool) -> None:
    """
    Purpose: Verify access logs for probe/health/metrics are dropped.
    Why this matters: Scrapes and k8s probes otherwise drown real request logs.
    Setup summary: Filter sample uvicorn access lines; assert keep/drop.
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
def test_configure_logging__installs_access_filter_idempotently() -> None:
    """
    Purpose: Verify configure_logging attaches a single quiet-access filter.
    Why this matters: Re-configure must not stack duplicate filters.
    Setup summary: Clear filters, configure twice, assert one _QuietAccess.
    """
    access = logging.getLogger("uvicorn.access")
    access.filters.clear()

    configure_logging(level="INFO")
    configure_logging(level="INFO")

    assert sum(isinstance(f, _QuietAccess) for f in access.filters) == 1
