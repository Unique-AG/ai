from __future__ import annotations

from typing import Any

from unique_search_proxy_core.schema import (
    ErrorDetail,
    ProxyErrorCode,
    ProxyRequestType,
)


class ProxyError(Exception):
    """Base exception for proxy failures with a stable error code."""

    code: ProxyErrorCode = ProxyErrorCode.BAD_REQUEST
    status_code: int = 400
    retryable: bool = False
    message: str
    request: ProxyRequestType | None
    provider: str | None
    details: list[dict[str, Any]] | None
    upstream_raw: Any | None

    def __init__(
        self,
        message: str,
        *,
        request: ProxyRequestType | None = None,
        provider: str | None = None,
        retryable: bool | None = None,
        details: list[dict[str, Any]] | None = None,
        upstream_raw: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.request = request
        self.provider = provider
        if retryable is not None:
            self.retryable = retryable
        self.details = details
        self.upstream_raw = upstream_raw

    def to_detail(self) -> ErrorDetail:
        return ErrorDetail(
            code=self.code.value,
            message=self.message,
            request=self.request,
            provider=self.provider,
            retryable=self.retryable,
            details=self.details,
            raw=self.upstream_raw,
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

    def __init__(
        self,
        *,
        missing_env_vars: list[str] | None = None,
    ) -> None:
        if missing_env_vars:
            env_list = ", ".join(missing_env_vars)
            message = (
                f"Provider is not configured. Set environment variable(s): {env_list}"
            )
            details = [{"envVar": env_var} for env_var in missing_env_vars]
        else:
            message = "Provider is not registered or not configured"
            details = None
        super().__init__(message, details=details)
        self.missing_env_vars = missing_env_vars or []


def attach_request_context(
    exc: ProxyError,
    *,
    request: ProxyRequestType,
    provider: str,
) -> ProxyError:
    """Set request route and payload provider id on a proxy error."""
    exc.request = request
    exc.provider = provider
    return exc


class UpstreamTimeoutError(ProxyError):
    code = ProxyErrorCode.UPSTREAM_TIMEOUT
    status_code = 504
    retryable = True


class EmptySearchResultsError(ProxyError):
    code = ProxyErrorCode.EMPTY_SEARCH_RESULTS
    status_code = 404
    retryable = False
