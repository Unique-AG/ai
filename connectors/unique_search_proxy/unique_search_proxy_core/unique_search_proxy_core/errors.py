from __future__ import annotations

from typing import Any

from unique_search_proxy_core.schema import (
    ErrorDetail,
    ProxyErrorCode,
)


class ProxyError(Exception):
    """Base exception for proxy failures with a stable error code."""

    code: ProxyErrorCode = ProxyErrorCode.BAD_REQUEST
    status_code: int = 400
    retryable: bool = False

    def __init__(
        self,
        message: str,
        *,
        engine: str | None = None,
        crawler: str | None = None,
        retryable: bool | None = None,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.engine = engine
        self.crawler = crawler
        if retryable is not None:
            self.retryable = retryable
        self.details = details

    def to_detail(self) -> ErrorDetail:
        return ErrorDetail(
            code=self.code.value,
            message=self.message,
            engine=self.engine,
            crawler=self.crawler,
            retryable=self.retryable,
            details=self.details,
        )


class BadRequestProxyError(ProxyError):
    code = ProxyErrorCode.BAD_REQUEST
    status_code = 400


class ValidationProxyError(ProxyError):
    code = ProxyErrorCode.VALIDATION_ERROR
    status_code = 422


class ForbiddenTargetError(ProxyError):
    code = ProxyErrorCode.FORBIDDEN_TARGET
    status_code = 403


class RateLimitedError(ProxyError):
    code = ProxyErrorCode.RATE_LIMITED
    status_code = 429

    def __init__(
        self,
        message: str,
        *,
        retry_after_seconds: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, retryable=True, **kwargs)
        self.retry_after_seconds = retry_after_seconds


class UpstreamError(ProxyError):
    code = ProxyErrorCode.UPSTREAM_ERROR
    status_code = 502
    retryable = True


class EngineNotConfiguredError(ProxyError):
    code = ProxyErrorCode.ENGINE_NOT_CONFIGURED
    status_code = 503

    def __init__(self, provider: str, *, kind: str = "engine") -> None:
        super().__init__(
            f"{kind.capitalize()} '{provider}' is not registered or not configured",
            engine=provider if kind == "engine" else None,
            crawler=provider if kind == "crawler" else None,
        )
        self.provider = provider
        self.kind = kind


class UpstreamTimeoutError(ProxyError):
    code = ProxyErrorCode.UPSTREAM_TIMEOUT
    status_code = 504
    retryable = True


class EmptySearchResultsError(ProxyError):
    code = ProxyErrorCode.EMPTY_SEARCH_RESULTS
    status_code = 404
    retryable = False
