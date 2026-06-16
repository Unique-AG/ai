from __future__ import annotations

from typing import Any, NoReturn

import httpx
from unique_search_proxy_core.errors import RateLimitedError, UpstreamError
from unique_search_proxy_core.schema import (
    CrawlUrlResult,
    PerUrlError,
    ProxyErrorCode,
)


def upstream_response_raw(response: httpx.Response) -> Any:
    """Capture upstream body for debugging (JSON when possible, else text wrapper)."""
    try:
        return response.json()
    except ValueError:
        text = response.text
        if text:
            return {"httpStatus": response.status_code, "body": text}
        return {"httpStatus": response.status_code}


def transport_error_raw(exc: Exception) -> dict[str, str]:
    """Minimal raw payload when no upstream HTTP body was received."""
    return {"transportError": str(exc)}


def upstream_error_message(
    source: httpx.Response | dict[str, Any],
    *,
    provider_label: str,
    detail_keys: tuple[str, ...] = ("message", "error", "detail"),
    nested_error_keys: tuple[str, ...] = ("message", "detail"),
) -> str:
    """Build a human-readable message from an upstream JSON body or HTTP response."""
    if isinstance(source, httpx.Response):
        status_code = source.status_code
        try:
            payload = source.json()
        except ValueError:
            return f"{provider_label} failed with HTTP {status_code}"
        message = f"{provider_label} returned HTTP {status_code}"
    else:
        payload = source
        message = f"{provider_label} failed"

    if not isinstance(payload, dict):
        return message

    for key in detail_keys:
        detail = payload.get(key)
        if isinstance(detail, str) and detail.strip():
            return f"{message}: {detail}"
        if isinstance(detail, dict):
            for nested_key in nested_error_keys:
                nested = detail.get(nested_key)
                if isinstance(nested, str) and nested.strip():
                    return f"{message}: {nested}"

    return message


def crawl_upstream_error(
    url: str,
    message: str,
    *,
    raw: Any | None = None,
    content_type: str | None = "text/markdown",
    code: str = ProxyErrorCode.UPSTREAM_ERROR.value,
) -> CrawlUrlResult:
    """Build a per-URL crawl failure with optional upstream response attached."""
    return CrawlUrlResult(
        url=url,
        content=None,
        content_type=content_type,
        error=PerUrlError(code=code, message=message),
        raw=raw,
    )


def raise_for_upstream_response(
    response: httpx.Response,
    *,
    provider_label: str,
    detail_keys: tuple[str, ...] = ("message", "error", "detail"),
    nested_error_keys: tuple[str, ...] = ("message", "detail"),
    rate_limited_message: str | None = None,
) -> None:
    """Raise when an upstream HTTP response indicates failure."""
    if response.is_success:
        return

    raw = upstream_response_raw(response)

    if response.status_code == 429:
        retry_after_raw = response.headers.get("Retry-After")
        retry_after: int | None = None
        if retry_after_raw is not None:
            try:
                retry_after = int(retry_after_raw)
            except ValueError:
                retry_after = None
        message = rate_limited_message or f"{provider_label} rate limit exceeded"
        raise RateLimitedError(
            message,
            retry_after_seconds=retry_after,
            upstream_raw=raw,
        )

    message = upstream_error_message(
        response,
        provider_label=provider_label,
        detail_keys=detail_keys,
        nested_error_keys=nested_error_keys,
    )
    raise UpstreamError(message, upstream_raw=raw)


def raise_batch_upstream_failure(
    message: str,
    *,
    raw: Any | None = None,
) -> NoReturn:
    """Raise for crawl tier-1 failures (entire provider batch call failed)."""
    raise UpstreamError(message, upstream_raw=raw)
