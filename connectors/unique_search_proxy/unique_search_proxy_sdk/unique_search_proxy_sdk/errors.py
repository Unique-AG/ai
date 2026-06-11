"""Map proxy HTTP error payloads to typed exceptions for SDK callers."""

from __future__ import annotations

from typing import Any

import httpx
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
    attach_request_context,
)
from unique_search_proxy_core.schema import ErrorResponse, ProxyErrorCode

_CODE_TO_EXCEPTION: dict[str, type[ProxyError]] = {
    ProxyErrorCode.BAD_REQUEST.value: BadRequestProxyError,
    ProxyErrorCode.VALIDATION_ERROR.value: ValidationProxyError,
    ProxyErrorCode.FORBIDDEN_TARGET.value: ForbiddenTargetError,
    ProxyErrorCode.RATE_LIMITED.value: RateLimitedError,
    ProxyErrorCode.UPSTREAM_ERROR.value: UpstreamError,
    ProxyErrorCode.ENGINE_NOT_CONFIGURED.value: EngineNotConfiguredError,
    ProxyErrorCode.UPSTREAM_TIMEOUT.value: UpstreamTimeoutError,
    ProxyErrorCode.EMPTY_SEARCH_RESULTS.value: EmptySearchResultsError,
}


class UniqueSearchProxyClientError(Exception):
    """Transport or unexpected response errors from the HTTP SDK."""


def _request_context_fields(detail: dict[str, Any]) -> dict[str, Any]:
    request = detail.get("request")
    provider = detail.get("provider")
    if request is not None:
        return {
            "request": request,
            "provider": provider,
        }
    return {}


def _raise_from_error_detail(detail: dict[str, Any], *, status_code: int) -> None:
    code = str(detail.get("code", ProxyErrorCode.BAD_REQUEST.value))
    message = str(detail.get("message", ""))
    request_context = _request_context_fields(detail)

    if code == ProxyErrorCode.ENGINE_NOT_CONFIGURED.value:
        details_list = detail.get("details") or []
        missing_env_vars = [
            item["envVar"]
            for item in details_list
            if isinstance(item, dict) and "envVar" in item
        ]
        exc = EngineNotConfiguredError(missing_env_vars=missing_env_vars or None)
        if request_context:
            attach_request_context(exc, **request_context)  # type: ignore[arg-type]
        exc.status_code = status_code
        raise exc

    exc_type = _CODE_TO_EXCEPTION.get(code, ProxyError)
    exc = exc_type(
        message,
        retryable=bool(detail.get("retryable", False)),
        details=detail.get("details"),
        **request_context,
    )
    exc.status_code = status_code
    raise exc


def raise_for_proxy_response(response: httpx.Response) -> None:
    """Raise a ``ProxyError`` subclass when the response body is a proxy error envelope."""
    if response.is_success:
        return

    detail: dict[str, Any] | None = None
    try:
        payload = response.json()
        if isinstance(payload, dict) and "error" in payload:
            detail = ErrorResponse.model_validate(payload).error.model_dump(
                by_alias=False,
            )
    except Exception:
        detail = None

    if detail is not None:
        _raise_from_error_detail(detail, status_code=response.status_code)
        return

    raise UniqueSearchProxyClientError(
        f"Request failed with status {response.status_code}: {response.text}",
    )
