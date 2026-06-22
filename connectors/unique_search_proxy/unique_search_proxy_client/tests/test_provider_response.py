from __future__ import annotations

import httpx
import pytest
from unique_search_proxy_core.errors import UpstreamError
from unique_search_proxy_core.schema import ProxyErrorCode

from unique_search_proxy_client.web.core.provider_response import (
    crawl_upstream_error,
    raise_for_upstream_response,
    transport_error_raw,
    upstream_error_message,
    upstream_response_raw,
)


@pytest.mark.ai
def test_upstream_response_raw_parses_json() -> None:
    response = httpx.Response(200, json={"code": 401, "message": "nope"})
    assert upstream_response_raw(response) == {"code": 401, "message": "nope"}


@pytest.mark.ai
def test_upstream_response_raw_wraps_plain_text() -> None:
    response = httpx.Response(502, text="bad gateway")
    assert upstream_response_raw(response) == {
        "httpStatus": 502,
        "body": "bad gateway",
    }


@pytest.mark.ai
def test_crawl_upstream_error_attaches_raw_payload() -> None:
    raw = {"code": 401, "message": "Invalid Jina API key"}
    result = crawl_upstream_error(
        "https://example.com",
        "Jina reader error (401): Invalid Jina API key",
        raw=raw,
    )

    assert result.error is not None
    assert result.error.code == ProxyErrorCode.UPSTREAM_ERROR.value
    assert result.raw == raw


@pytest.mark.ai
def test_transport_error_raw() -> None:
    exc = httpx.ConnectError("connection refused")
    assert transport_error_raw(exc) == {"transportError": "connection refused"}


@pytest.mark.ai
def test_upstream_error_message_nested_google_shape() -> None:
    response = httpx.Response(
        403,
        json={"error": {"message": "Daily Limit Exceeded"}},
    )
    message = upstream_error_message(
        response,
        provider_label="Google Custom Search API",
        detail_keys=("error",),
        nested_error_keys=("message",),
    )
    assert message == "Google Custom Search API returned HTTP 403: Daily Limit Exceeded"


@pytest.mark.ai
def test_raise_for_upstream_response_attaches_raw() -> None:
    response = httpx.Response(502, json={"error": "upstream down"})
    with pytest.raises(UpstreamError) as exc_info:
        raise_for_upstream_response(
            response,
            provider_label="Example API",
        )
    assert exc_info.value.upstream_raw == {"error": "upstream down"}
