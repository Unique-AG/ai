import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import unique_sdk

from unique_toolkit.language_model import LanguageModelCallError
from unique_toolkit.language_model.functions import complete_async
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import LanguageModelMessages

pytestmark = pytest.mark.ai

_FILTER_MESSAGE = (
    "The response was filtered due to the prompt triggering the content "
    "filter management policy of the AI model. Please modify your prompt and retry."
)


class _RecordingServer(ThreadingHTTPServer):
    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.responses: list[tuple[int, dict[str, object]]] = []
        self.hits = 0


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        if length:
            self.rfile.read(length)
        server = self.server
        assert isinstance(server, _RecordingServer)
        server.hits += 1
        status, payload = server.responses[
            min(server.hits - 1, len(server.responses) - 1)
        ]
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture
def llm_error_server():
    """Serve contract error bodies and point the SDK at that server."""
    server = _RecordingServer()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    previous = (unique_sdk.api_base, unique_sdk.api_key, unique_sdk.app_id)
    unique_sdk.api_base = f"http://127.0.0.1:{server.server_address[1]}"
    unique_sdk.api_key = "test-key"
    unique_sdk.app_id = "app"
    try:
        yield server
    finally:
        unique_sdk.api_base, unique_sdk.api_key, unique_sdk.app_id = previous
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def _envelope(code: str, message: str, params: dict[str, object]) -> dict[str, object]:
    return {
        "error": {
            "type": "invalid_request_error",
            "code": code,
            "message": message,
            "params": params,
        }
    }


async def _complete() -> None:
    await complete_async(
        company_id="company",
        user_id="user",
        messages=LanguageModelMessages([]),
        model_name=LanguageModelName.AZURE_GPT_4_0613,
    )


async def test_complete_async__content_filter_over_http(
    llm_error_server: _RecordingServer,
) -> None:
    """Purpose: Verify a real HTTP 400 becomes LanguageModelCallError.
    Why this matters: This is the path Document Search uses for keyword extraction.
    Setup summary: A local server returns the content-filter envelope once.
    """
    llm_error_server.responses.append(
        (
            400,
            _envelope(
                "content_filter",
                _FILTER_MESSAGE,
                {
                    "retryable": False,
                    "correlationId": "corr-1",
                    "model": "gpt-4o-2024-11-20",
                },
            ),
        )
    )

    with pytest.raises(LanguageModelCallError) as caught:
        await _complete()

    error = caught.value
    assert error.code == "content_filter"
    assert error.user_message == _FILTER_MESSAGE
    assert error.retryable is False
    assert error.correlation_id == "corr-1"
    assert error.http_status == 400
    assert "(Original error)" not in str(error)
    assert error.__cause__ is not None
    assert llm_error_server.hits == 1


async def test_complete_async__rate_limit_over_http_is_not_retried_by_sdk(
    llm_error_server: _RecordingServer,
) -> None:
    """Purpose: Verify a contract 429 is surfaced once, without an SDK retry.
    Why this matters: 429 is a 4xx. The SDK must not retry it or wrap it.
    Setup summary: A local server returns rate_limited with retryAfterSeconds.
    """
    llm_error_server.responses.append(
        (
            429,
            _envelope(
                "rate_limited",
                "The model is receiving too many requests. Please retry.",
                {"retryable": True, "correlationId": "corr-2", "retryAfterSeconds": 30},
            ),
        )
    )

    with pytest.raises(LanguageModelCallError) as caught:
        await _complete()

    error = caught.value
    assert error.code == "rate_limited"
    assert error.retryable is True
    assert error.correlation_id == "corr-2"
    assert llm_error_server.hits == 1


async def test_complete_async__retries_5xx_using_retry_after(
    llm_error_server: _RecordingServer,
) -> None:
    """Purpose: Verify a retryable 5xx is tried three times, then re-raised as-is.
    Why this matters: The last attempt must keep code and the user message.
    Setup summary: A local server always returns provider_unavailable with a zero wait.
    """
    llm_error_server.responses.append(
        (
            503,
            _envelope(
                "provider_unavailable",
                "The model provider is unavailable. Please retry.",
                {"retryable": True, "correlationId": "corr-3", "retryAfterSeconds": 0},
            ),
        )
    )

    with pytest.raises(LanguageModelCallError) as caught:
        await _complete()

    error = caught.value
    assert error.code == "provider_unavailable"
    assert error.user_message == "The model provider is unavailable. Please retry."
    assert error.retryable is True
    assert error.correlation_id == "corr-3"
    assert llm_error_server.hits == 3
