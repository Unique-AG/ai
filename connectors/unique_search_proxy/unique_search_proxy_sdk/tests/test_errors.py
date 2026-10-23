from __future__ import annotations

import httpx
import pytest
from unique_search_proxy_core.errors import ResponseTooLargeError

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
