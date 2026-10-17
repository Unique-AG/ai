from __future__ import annotations

import logging

from starlette.types import ASGIApp, Receive, Scope, Send
from unique_search_proxy_core.context import LOCAL_REQUEST_CONTEXT, RequestContext
from unique_search_proxy_core.errors import BadRequestProxyError, ValidationProxyError

from unique_search_proxy_client.web.context import (
    bind_request_context,
    reset_request_context,
)
from unique_search_proxy_client.web.error_handlers import proxy_error_response
from unique_search_proxy_client.web.monitoring.metrics import (
    record_unattributed_request,
)
from unique_search_proxy_client.web.settings.app import app_settings

_LOGGER = logging.getLogger(__name__)

_CONTEXT_EXCLUDED_PATHS = frozenset(
    {
        "/",
        "/health",
        "/ready",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
)

_ATTRIBUTION_EXEMPT_PREFIX = "/v1/configuration/"


def _headers_from_scope(scope: Scope) -> dict[str, str]:
    return {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in scope.get("headers", [])
    }


class RequestContextMiddleware:
    """Enforce tenant context headers on /v1 routes and bind them for logging.

    Implemented as pure ASGI middleware (not ``BaseHTTPMiddleware``) so the
    bound context stays active for the whole request lifecycle — including
    response send, which is when Uvicorn emits its access log line.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not path.startswith("/v1") or path in _CONTEXT_EXCLUDED_PATHS:
            await self.app(scope, receive, send)
            return

        headers = _headers_from_scope(scope)
        missing = RequestContext.missing_headers(headers)
        if missing and app_settings.require_context_headers:
            details = [
                {
                    "loc": ["header", header_name],
                    "msg": "Field required",
                    "type": "missing",
                }
                for header_name in missing
            ]
            response = proxy_error_response(
                ValidationProxyError(
                    f"Missing required context headers: {', '.join(missing)}",
                    details=details,
                ),
            )
            await response(scope, receive, send)
            return

        context = RequestContext.from_headers(
            headers,
            fallback=LOCAL_REQUEST_CONTEXT,
        )
        token = bind_request_context(context)
        try:
            # Warn and count by default; reject only when the setting is on.
            if not context.is_attributed and not path.startswith(
                _ATTRIBUTION_EXEMPT_PREFIX
            ):
                invalid = context.invalid_identity_headers
                record_unattributed_request(context.entry_point.value)
                _LOGGER.warning("Unattributed request, invalid headers: %s", invalid)
                if app_settings.reject_unattributed_requests:
                    response = proxy_error_response(
                        BadRequestProxyError(
                            f"Invalid context headers: {', '.join(invalid)}",
                            details=[
                                {
                                    "loc": ["header", header_name],
                                    "msg": "Must be a numeric id",
                                    "type": "invalid",
                                }
                                for header_name in invalid
                            ],
                        ),
                    )
                    await response(scope, receive, send)
                    return
            await self.app(scope, receive, send)
        finally:
            reset_request_context(token)


__all__ = ["RequestContextMiddleware"]
