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


def test_body_for_error_message_redacted_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", raising=False)

    result = _util.body_for_error_message(b'{"text":"client portfolio details"}')

    assert "client portfolio details" not in str(result)
    assert str(result) == "<redacted 35 bytes>"


def test_body_for_error_message_passthrough_when_insecure_flag_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", "true")

    body = b'{"text":"client portfolio details"}'
    assert _util.body_for_error_message(body) is body


def test_invalid_response_body_error_message_is_redacted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", raising=False)

    from unique_sdk._api_requestor import APIRequestor
    from unique_sdk._error import APIError

    requestor = APIRequestor(
        key="sk-test", app_id="app-test", user_id="user-1", company_id="company-1"
    )
    # Latin-1 bytes that cannot decode as UTF-8 → interpret_response raises.
    bad_body = 'note for Dr. Client Name: "caf\xe9"'.encode("latin-1")

    with pytest.raises(APIError) as exc_info:
        requestor.interpret_response(bad_body, 200, {})

    assert "Client Name" not in str(exc_info.value)
    assert "<redacted" in str(exc_info.value)


def test_error_params_redacted_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", raising=False)

    assert _util.error_params_for_log({"text": "Dr. Client Name"}) == "<redacted>"
    assert _util.error_params_for_log(None) is None


def test_error_params_passthrough_when_insecure_flag_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", "true")

    params = {"text": "Dr. Client Name"}
    assert _util.error_params_for_log(params) is params
