from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from unique_search_proxy.web.core.schema import (
    ErrorDetail,
    ErrorResponse,
    ProxyErrorCode,
)

_LOGGER = logging.getLogger(__name__)


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


def proxy_error_response(exc: ProxyError) -> JSONResponse:
    headers: dict[str, str] = {}
    if isinstance(exc, RateLimitedError) and exc.retry_after_seconds is not None:
        headers["Retry-After"] = str(exc.retry_after_seconds)

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.to_detail()).model_dump(by_alias=True),
        headers=headers or None,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProxyError)
    async def proxy_error_handler(_request: Request, exc: ProxyError) -> JSONResponse:
        from unique_search_proxy.web.monitoring.metrics import (
            record_crawl_error,
            record_proxy_error,
            record_search_error,
        )

        record_proxy_error(exc.code.value)
        if exc.engine is not None:
            record_search_error(exc.engine, exc.code.value, 0.0)
        if exc.crawler is not None:
            record_crawl_error(exc.crawler, exc.code.value, 0.0)
        _LOGGER.warning("Proxy error [%s]: %s", exc.code.value, exc.message)
        return proxy_error_response(exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "loc": list(error.get("loc", ())),
                "msg": error.get("msg", ""),
                "type": error.get("type", ""),
            }
            for error in exc.errors()
        ]
        proxy_exc = ValidationProxyError(
            "Request validation failed",
            details=details,
        )
        return proxy_error_response(proxy_exc)

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(
        _request: Request, exc: ValidationError
    ) -> JSONResponse:
        details = [
            {
                "loc": list(error.get("loc", ())),
                "msg": error.get("msg", ""),
                "type": error.get("type", ""),
            }
            for error in exc.errors()
        ]
        proxy_exc = ValidationProxyError(
            "Request validation failed",
            details=details,
        )
        return proxy_error_response(proxy_exc)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        if exc.status_code == 404:
            proxy_exc = BadRequestProxyError(exc.detail or "Not found")
            response = proxy_error_response(proxy_exc)
            response.status_code = 404
            return response
        proxy_exc = ProxyError(str(exc.detail))
        proxy_exc.status_code = exc.status_code
        return proxy_error_response(proxy_exc)
