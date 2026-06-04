"""Shared types for Unique Search Proxy (no FastAPI / server dependencies)."""

from unique_search_proxy_core.errors import (
    BadRequestProxyError,
    EmptySearchResultsError,
    EngineNotConfiguredError,
    ForbiddenTargetError,
    ProxyError,
    RateLimitedError,
    UpstreamError,
    UpstreamTimeoutError,
    ValidationProxyError,
)
from unique_search_proxy_core.schema import (
    ErrorDetail,
    ErrorResponse,
    ProxyErrorCode,
    WebSearchResult,
)

__all__ = [
    "BadRequestProxyError",
    "EmptySearchResultsError",
    "EngineNotConfiguredError",
    "ErrorDetail",
    "ErrorResponse",
    "ForbiddenTargetError",
    "ProxyError",
    "ProxyErrorCode",
    "RateLimitedError",
    "UpstreamError",
    "UpstreamTimeoutError",
    "ValidationProxyError",
    "WebSearchResult",
]
