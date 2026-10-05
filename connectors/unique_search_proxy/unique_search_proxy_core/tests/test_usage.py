"""Tests for the structured usage record."""

from __future__ import annotations

import json
import logging

import pytest

from unique_search_proxy_core.context import EntryPoint
from unique_search_proxy_core.usage import UsageRecord, record_usage

pytestmark = pytest.mark.ai


def _record(**overrides: object) -> UsageRecord:
    fields: dict[str, object] = {
        "company_id": "1",
        "user_id": "2",
        "chat_id": "chat-1",
        "entry_point": EntryPoint.PUBLIC_API,
        "endpoint": "search",
        "provider": "google",
        "units": 1,
        "status": "success",
        "duration_ms": 120,
    }
    return UsageRecord(**{**fields, **overrides})


def test_record_usage_emits_one_json_line_with_fixed_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="unique_search_proxy_core.usage"):
        record_usage(_record())

    assert len(caplog.records) == 1
    payload = json.loads(caplog.records[0].getMessage())
    assert set(payload) == {
        "event",
        "request_id",
        "timestamp",
        "company_id",
        "user_id",
        "chat_id",
        "entry_point",
        "endpoint",
        "provider",
        "units",
        "status",
        "duration_ms",
    }
    assert payload["event"] == "web_search_usage"
    assert payload["entry_point"] == "public_api"


def test_each_record_gets_its_own_request_id() -> None:
    assert _record().request_id != _record().request_id
