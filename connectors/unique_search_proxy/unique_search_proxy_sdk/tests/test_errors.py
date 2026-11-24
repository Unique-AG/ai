from __future__ import annotations

import httpx
import pytest
from unique_search_proxy_core.errors import RateLimitedError, ResponseTooLargeError

from unique_search_proxy_sdk.errors import raise_for_proxy_response


@pytest.mark.ai
def test_raise_for_proxy_response__raises_response_too_large__for_its_code() -> None:
    """
    Purpose: Verify the SDK maps RESPONSE_TOO_LARGE to ResponseTooLargeError.
    Why this matters: SDK callers handle oversized upstream bodies by type.
    Setup summary: 502 error envelope with the code; assert the typed error.
    """
    response = httpx.Response(
        502,
        json={
            "error": {
                "code": "RESPONSE_TOO_LARGE",
                "message": "Upstream response exceeded the 4096 byte limit",
                "retryable": False,
            },
        },
    )

    with pytest.raises(ResponseTooLargeError) as exc_info:
        raise_for_proxy_response(response)

    assert exc_info.value.status_code == 502
    assert exc_info.value.retryable is False


@pytest.mark.ai
def test_raise_for_proxy_response__raises_rate_limited__for_its_code() -> None:
    """
    Purpose: Verify the SDK maps RATE_LIMITED to RateLimitedError.
    Why this matters: Callers fall back or retry on RateLimitedError; building it
        used to fail with a TypeError, so a busy proxy dropped whole search steps.
    Setup summary: 429 error envelope with the code; assert the typed error.
    """
    response = httpx.Response(
        429,
        json={
            "error": {
                "code": "RATE_LIMITED",
                "message": "Crawl capacity is in use",
                "retryable": True,
            },
        },
    )

    with pytest.raises(RateLimitedError) as exc_info:
        raise_for_proxy_response(response)

    assert exc_info.value.status_code == 429
    assert exc_info.value.retryable is True


@pytest.mark.ai
def test_rate_limited_error__is_retryable__by_default() -> None:
    """
    Purpose: Verify RateLimitedError is retryable when no flag is passed.
    Why this matters: The proxy raises it without the flag and sends the flag to
        callers in the error envelope.
    Setup summary: Build the error with only a message; assert retryable.
    """
    assert RateLimitedError("Crawl capacity is in use").retryable is True
