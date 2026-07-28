"""Shared types for Unique Search Proxy (no FastAPI / server dependencies)."""

from unique_search_proxy_core.context import (
    CHAT_ID_HEADER,
    COMPANY_ID_HEADER,
    LOCAL_REQUEST_CONTEXT,
    USER_ID_HEADER,
    RequestContext,
)
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
    CrawlResponse,
    ErrorDetail,
    ErrorResponse,
    ProvidersListResponse,
    ProxyErrorCode,
    SearchResponse,
    WebSearchResult,
)

__all__ = [
    "CHAT_ID_HEADER",
    "COMPANY_ID_HEADER",
    "LOCAL_REQUEST_CONTEXT",
    "RequestContext",
    "USER_ID_HEADER",
    "BadRequestProxyError",
    "CrawlResponse",
    "EmptySearchResultsError",
    "EngineNotConfiguredError",
    "ErrorDetail",
    "ErrorResponse",
    "ForbiddenTargetError",
    "ProvidersListResponse",
    "ProxyError",
    "ProxyErrorCode",
    "RateLimitedError",
    "SearchResponse",
    "UpstreamError",
    "UpstreamTimeoutError",
    "ValidationProxyError",
    "WebSearchResult",
]
