"""ProxyError construction — every subclass must accept the kwargs the SDK's
generic error-detail mapping forwards for every error code, including
``retryable`` (see unique_search_proxy_sdk.errors._raise_from_error_detail)."""

import pytest

from unique_search_proxy_core.errors import (
    BadRequestProxyError,
    EmptySearchResultsError,
    ForbiddenTargetError,
    ProxyError,
    RateLimitedError,
    UpstreamError,
    UpstreamTimeoutError,
    ValidationProxyError,
)


class TestProxyErrorConstruction:
    @pytest.mark.ai
    @pytest.mark.parametrize(
        "exc_type",
        [
            ProxyError,
            BadRequestProxyError,
            ValidationProxyError,
            ForbiddenTargetError,
            RateLimitedError,
            UpstreamError,
            UpstreamTimeoutError,
            EmptySearchResultsError,
        ],
    )
    def test_accepts_generic_error_detail_kwargs(
        self, exc_type: type[ProxyError]
    ) -> None:
        # Mirrors unique_search_proxy_sdk.errors._raise_from_error_detail,
        # which builds every mapped exception type with this exact call shape.
        exc = exc_type(
            "boom",
            retryable=True,
            details=None,
            upstream_raw=None,
        )
        assert exc.message == "boom"

    @pytest.mark.ai
    def test_rate_limited_is_always_retryable(self) -> None:
        # Hardcoded True regardless of what the wire payload says.
        exc = RateLimitedError("slow down", retryable=False, retry_after_seconds=30)
        assert exc.retryable is True
        assert exc.retry_after_seconds == 30
