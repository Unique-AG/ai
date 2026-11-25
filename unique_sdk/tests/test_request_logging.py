"""Request/response debug logging must not emit payloads by default."""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_sdk import _util
from unique_sdk._api_requestor import APIRequestor
from unique_sdk._error import APIConnectionError, InvalidRequestError


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

    result = _util.redacted_body_for_error_message(
        b'{"text":"client portfolio details"}'
    )

    assert "client portfolio details" not in str(result)
    assert str(result) == "<redacted 35 bytes>"


def test_body_for_error_message_passthrough_when_insecure_flag_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", "true")

    body = b'{"text":"client portfolio details"}'
    assert _util.redacted_body_for_error_message(body) is body


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

    assert _util.redacted_error_params({"text": "Dr. Client Name"}) == "<redacted>"
    assert _util.redacted_error_params(None) is None


def test_error_params_passthrough_when_insecure_flag_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", "true")

    params = {"text": "Dr. Client Name"}
    assert _util.redacted_error_params(params) is params


# Request URL logging.

_SENTINEL = "SENTINEL-7f3a"
_FOLDER_PATH = f"/home/Jane.Doe/skills-{_SENTINEL}"


def _requestor_with_client(client: Any) -> APIRequestor:
    requestor = APIRequestor(
        user_id="user_id", company_id="company_id", key="api_key", app_id="app_id"
    )
    requestor._client = client
    return requestor


def _sync_client(status: int = 200) -> MagicMock:
    client = MagicMock()
    client.name = "test"
    client.request.return_value = (b"{}", status, {})
    return client


def _async_client(status: int = 200) -> MagicMock:
    client = MagicMock()
    client.name = "test"
    client.request_async = AsyncMock(return_value=(b"{}", status, {}))
    return client


def _messages(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [record.getMessage() for record in caplog.records]


def _url_lines(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [m for m in _messages(caplog) if "path=" in m]


def test_AI_get_request_logs_path_without_query_string(
    monkeypatch: pytest.MonkeyPatch,
    capture_unique_debug_logs: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.delenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", raising=False)
    client = _sync_client()

    _requestor_with_client(client).request_raw(
        "get", "/folder/info", {"folderPath": _FOLDER_PATH, "take": 5}
    )

    # The request itself still carries the query string.
    assert _SENTINEL in client.request.call_args.args[1]
    lines = _url_lines(capture_unique_debug_logs)
    assert len(lines) == 2  # request and response
    for message in _messages(capture_unique_debug_logs):
        assert _SENTINEL not in message
        assert "Jane.Doe" not in message
        assert "?" not in message
    for line in lines:
        assert "/folder/info" in line


@pytest.mark.asyncio
async def test_AI_async_get_request_logs_path_without_query_string(
    monkeypatch: pytest.MonkeyPatch,
    capture_unique_debug_logs: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.delenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", raising=False)
    client = _async_client()

    await _requestor_with_client(client).request_raw_async(
        "delete", "/folder/info", {"folderPath": _FOLDER_PATH}
    )

    assert _SENTINEL in client.request_async.call_args.args[1]
    lines = _url_lines(capture_unique_debug_logs)
    assert len(lines) == 2
    for message in _messages(capture_unique_debug_logs):
        assert _SENTINEL not in message
        assert "?" not in message
    for line in lines:
        assert "/folder/info" in line


def test_AI_get_request_logs_query_param_names_not_values(
    monkeypatch: pytest.MonkeyPatch,
    capture_unique_debug_logs: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.delenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", raising=False)

    _requestor_with_client(_sync_client()).request_raw(
        "get", "/folder/info", {"folderPath": _FOLDER_PATH, "take": 5}
    )

    request_line = next(
        m
        for m in _messages(capture_unique_debug_logs)
        if "message='Request to Unique'" in m
    )
    assert "query_keys=folderPath,take" in request_line
    assert _SENTINEL not in request_line


def test_AI_get_request_logs_full_url_when_insecure_flag_set(
    monkeypatch: pytest.MonkeyPatch,
    capture_unique_debug_logs: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", "true")

    _requestor_with_client(_sync_client()).request_raw(
        "get", "/folder/info", {"folderPath": _FOLDER_PATH}
    )

    lines = _url_lines(capture_unique_debug_logs)
    assert len(lines) == 2
    for line in lines:
        assert "/folder/info?folderPath=" in line
        assert _SENTINEL in line


def test_AI_post_request_log_line_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    capture_unique_debug_logs: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.delenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", raising=False)
    client = _sync_client()

    _requestor_with_client(client).request_raw(
        "post", "/folder", {"paths": [_FOLDER_PATH]}
    )

    # POST params go in the body, which is redacted; no query_keys field.
    assert client.request.call_args.args[3] == {"paths": [_FOLDER_PATH]}
    request_line = next(
        m
        for m in _messages(capture_unique_debug_logs)
        if "message='Request to Unique'" in m
    )
    assert "/folder " in request_line or request_line.endswith("/folder")
    assert "query_keys" not in request_line
    for message in _messages(capture_unique_debug_logs):
        assert _SENTINEL not in message


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://gw.example/a/b?x=1&y=2", "https://gw.example/a/b"),
        ("https://gw.example/a/b", "https://gw.example/a/b"),
        ("https://gw.example/a/b?x=1#frag", "https://gw.example/a/b"),
    ],
)
def test_AI_url_for_log_drops_query_and_fragment(
    monkeypatch: pytest.MonkeyPatch, url: str, expected: str
) -> None:
    monkeypatch.delenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", raising=False)

    assert _util.url_for_log(url) == expected


# Server error messages echo request input.


def test_AI_error_received_log_redacts_server_message(
    monkeypatch: pytest.MonkeyPatch,
    capture_unique_debug_logs: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.delenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", raising=False)
    server_message = f"Folder with id or path {_FOLDER_PATH} not found"
    body = {"error": {"message": server_message, "type": "not_found"}}

    with pytest.raises(InvalidRequestError) as excinfo:
        _requestor_with_client(_sync_client()).handle_error_response(
            "{}", 404, body, {}
        )

    # The caller still gets the server's message on the exception.
    assert _SENTINEL in str(excinfo.value)
    error_line = next(
        m
        for m in _messages(capture_unique_debug_logs)
        if "message='Unique error received'" in m
    )
    assert "error_message=<redacted>" in error_line
    assert "error_code=404" in error_line
    assert _SENTINEL not in error_line


def test_AI_error_received_log_keeps_server_message_when_insecure_flag_set(
    monkeypatch: pytest.MonkeyPatch,
    capture_unique_debug_logs: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", "true")
    body = {"error": {"message": f"Folder {_SENTINEL} not found", "type": "x"}}

    with pytest.raises(InvalidRequestError):
        _requestor_with_client(_sync_client()).handle_error_response(
            "{}", 404, body, {}
        )

    error_line = next(
        m
        for m in _messages(capture_unique_debug_logs)
        if "message='Unique error received'" in m
    )
    assert _SENTINEL in error_line


# Connection errors quote the request URL.

_REQUESTS_CONNECTION_ERROR = (
    "HTTPSConnectionPool(host='gw.example', port=443): Max retries exceeded "
    f"with url: /public/chat-gen2/folder/info?folderPath={_FOLDER_PATH}&take=5 "
    "(Caused by NewConnectionError('Failed to establish a new connection'))"
)


def test_AI_connection_error_message_drops_url_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", raising=False)
    client = MagicMock()
    client.name = "test"
    client.request.side_effect = APIConnectionError(
        "Unexpected error communicating with Unique.",
        original_error=ConnectionError(_REQUESTS_CONNECTION_ERROR),
    )

    with pytest.raises(APIConnectionError) as excinfo:
        _requestor_with_client(client).request_raw(
            "get", "/folder/info", {"folderPath": _FOLDER_PATH}
        )

    message = str(excinfo.value)
    assert _SENTINEL not in message
    assert "with url: /public/chat-gen2/folder/info (Caused by" in message
    # The original exception stays available, unchanged, for callers.
    assert _SENTINEL in str(excinfo.value.original_error)


def test_AI_connection_error_message_keeps_url_query_when_insecure_flag_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", "true")
    error = APIConnectionError(
        "Unexpected error communicating with Unique.",
        original_error=ConnectionError(_REQUESTS_CONNECTION_ERROR),
    )

    assert _SENTINEL in str(error)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("url: /a/b?x=1&y=%2Fhome (Caused", "url: /a/b (Caused"),
        ("GET https://gw.example/a?x=1 failed", "GET https://gw.example/a failed"),
        ("'https://gw.example/a?x=1'", "'https://gw.example/a'"),
        ("GET /a?p=/home/Jane)Doe/private failed", "GET /a failed"),
        ("Is it done? Not yet.", "Is it done? Not yet."),
        ("no url here", "no url here"),
    ],
)
def test_AI_strip_url_queries(
    monkeypatch: pytest.MonkeyPatch, text: str, expected: str
) -> None:
    monkeypatch.delenv("INSECURE_UNIQUE_SDK_LOG_PAYLOADS", raising=False)

    assert _util.strip_url_queries(text) == expected
