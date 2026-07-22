"""Request/response debug logging must not emit payloads by default."""

from __future__ import annotations

import logging
from typing import Any

import pytest

from unique_sdk import _util


@pytest.fixture
def capture_unique_debug_logs(caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.DEBUG, logger="unique")
    return caplog


def _request_payload() -> dict[str, Any]:
    return {
        "messages": [
            {
                "role": "user",
                "content": "Draft a note for Dr. Client Name about portfolio PTY-0001",
            }
        ]
    }


def _request_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer secret-token",
        "Content-Type": "application/json",
        "x-user-id": "user-1",
        "x-company-id": "company-1",
    }


def test_request_details_redacted_by_default(
    monkeypatch: pytest.MonkeyPatch,
    capture_unique_debug_logs: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.delenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", raising=False)

    _util.log_request_details(
        data=_request_payload(),
        headers=_request_headers(),
        api_version="2023-12-06",
    )

    assert len(capture_unique_debug_logs.records) == 1
    message = capture_unique_debug_logs.records[0].getMessage()
    assert "message='Request details'" in message
    assert "data=<redacted>" in message
    assert "headers=<redacted>" in message
    assert "payload_bytes=" in message
    assert "Dr. Client Name" not in message
    assert "secret-token" not in message
    assert "Bearer" not in message


def test_response_body_redacted_by_default(
    monkeypatch: pytest.MonkeyPatch,
    capture_unique_debug_logs: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.delenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", raising=False)

    _util.log_response_body(body=b'{"text":"client portfolio details"}')

    assert len(capture_unique_debug_logs.records) == 1
    message = capture_unique_debug_logs.records[0].getMessage()
    assert "message='Unique response body'" in message
    assert "body=<redacted>" in message
    assert "payload_bytes=" in message
    assert "client portfolio details" not in message


def test_request_details_include_payload_when_insecure_flag_set(
    monkeypatch: pytest.MonkeyPatch,
    capture_unique_debug_logs: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", "true")

    _util.log_request_details(
        data=_request_payload(),
        headers=_request_headers(),
        api_version="2023-12-06",
    )

    assert len(capture_unique_debug_logs.records) == 1
    message = capture_unique_debug_logs.records[0].getMessage()
    assert "Dr. Client Name" in message
    assert "x-company-id" in message
    assert "secret-token" not in message
    assert "Authorization" in message
    assert "<redacted>" in message


def test_authorization_never_logged_even_with_insecure_flag(
    monkeypatch: pytest.MonkeyPatch,
    capture_unique_debug_logs: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", "true")

    _util.log_request_details(
        data={"ok": True},
        headers={"authorization": "Bearer another-secret"},
        api_version="2023-12-06",
    )

    message = capture_unique_debug_logs.records[0].getMessage()
    assert "another-secret" not in message
    assert "Bearer" not in message


def test_payload_byte_size_handles_bytes_and_str() -> None:
    assert _util._payload_byte_size(None) == 0
    assert _util._payload_byte_size(b"abc") == 3
    assert _util._payload_byte_size("é") == 2
    assert _util._payload_byte_size({"a": 1}) > 0
