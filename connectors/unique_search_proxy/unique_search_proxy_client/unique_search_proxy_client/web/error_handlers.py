from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from unique_search_proxy_core.errors import (
    BadRequestProxyError,
    ProxyError,
    RateLimitedError,
    ValidationProxyError,
)
from unique_search_proxy_core.schema import ErrorResponse

_LOGGER = logging.getLogger(__name__)


def proxy_error_response(exc: ProxyError) -> JSONResponse:
    headers: dict[str, str] = {}
    if isinstance(exc, RateLimitedError) and exc.retry_after_seconds is not None:
        headers["Retry-After"] = str(exc.retry_after_seconds)

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.to_detail()).model_dump(
            by_alias=True,
            exclude_none=True,
        ),
        headers=headers or None,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProxyError)
    async def proxy_error_handler(_request: Request, exc: ProxyError) -> JSONResponse:
        from unique_search_proxy_client.web.monitoring.metrics import (
            record_proxy_error,
        )

        record_proxy_error(exc.code.value)
        _LOGGER.warning(
            "Proxy error [%s] request=%s provider=%s: %s",
            exc.code.value,
            exc.request or "-",
            exc.provider or "-",
            exc.message,
        )
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
