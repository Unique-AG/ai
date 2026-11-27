from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

import httpx

from unique_search_proxy_core.url_safety.models import (
    BlockedCrawlTarget,
    CrawlTargetValidationError,
    ResolvedCrawlTarget,
    bypass_crawl_target,
)
from unique_search_proxy_core.url_safety.redirect import redirect_target_url
from unique_search_proxy_core.url_safety.resolver import resolve_crawl_target


def pinned_httpx_get_args(
    target: ResolvedCrawlTarget,
) -> tuple[str, dict[str, str], dict[str, str]]:
    """Build httpx GET url, headers, and extensions for DNS-pinned egress."""
    headers: dict[str, str] = {}
    if target.host_header is not None:
        headers["Host"] = target.host_header

    extensions: dict[str, str] = {}
    if target.sni_hostname is not None:
        extensions["sni_hostname"] = target.sni_hostname

    return target.request_url, headers, extensions


def _blocked_redirect(target: ResolvedCrawlTarget, reason: str) -> BlockedCrawlTarget:
    return BlockedCrawlTarget(
        hostname=target.hostname or None,
        category="redirect",
        reason=reason,
    )


def _next_redirect_url(
    response: httpx.Response,
    current_target: ResolvedCrawlTarget,
) -> str | None:
    try:
        next_url = redirect_target_url(response, current_target.normalized_url)
        if next_url is not None:
            parsed_next_url = urlsplit(next_url)
            _ = parsed_next_url.hostname
            _ = parsed_next_url.port
    except ValueError as exc:
        raise CrawlTargetValidationError(
            [
                _blocked_redirect(
                    current_target,
                    "Redirect target URL is missing or malformed",
                )
            ]
        ) from exc
    return next_url


@asynccontextmanager
async def safe_pinned_httpx_stream(
    client: httpx.AsyncClient,
    target: ResolvedCrawlTarget,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float | httpx.Timeout,
    max_redirect_hops: int,
    enforce_url_safety: bool,
) -> AsyncIterator[httpx.Response]:
    """Open a streamed GET, applying the original target's safety mode to redirects.

    Redirect hops are closed without reading their bodies. The final response
    is yielded unread so the caller decides how much of the body to consume;
    it is closed when the context exits.

    Raises:
        CrawlTargetValidationError: When a redirect is malformed, blocked, or
            exceeds ``max_redirect_hops``.
    """
    if max_redirect_hops < 0:
        raise ValueError("max_redirect_hops must be non-negative")

    current_target = target
    for redirects_followed in range(max_redirect_hops + 1):
        request_url, pin_headers, extensions = pinned_httpx_get_args(current_target)
        request = client.build_request(
            "GET",
            request_url,
            headers={**(headers or {}), **pin_headers},
            extensions=extensions or None,
            timeout=timeout,
        )
        response = await client.send(request, stream=True, follow_redirects=False)
        try:
            next_url = _next_redirect_url(response, current_target)
            if next_url is None:
                yield response
                return
            if redirects_followed == max_redirect_hops:
                raise CrawlTargetValidationError(
                    [
                        _blocked_redirect(
                            current_target,
                            "Maximum redirect hop count exceeded",
                        )
                    ]
                )
        finally:
            await response.aclose()

        current_target = (
            await resolve_crawl_target(next_url)
            if enforce_url_safety
            else bypass_crawl_target(next_url)
        )

    raise AssertionError("redirect loop must return or raise")


async def safe_pinned_httpx_get(
    client: httpx.AsyncClient,
    target: ResolvedCrawlTarget,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float | httpx.Timeout,
    max_redirect_hops: int,
    enforce_url_safety: bool,
) -> httpx.Response:
    """GET a target, applying the original target's safety mode to redirects."""
    async with safe_pinned_httpx_stream(
        client,
        target,
        headers=headers,
        timeout=timeout,
        max_redirect_hops=max_redirect_hops,
        enforce_url_safety=enforce_url_safety,
    ) as response:
        await response.aread()
    return response


__all__ = [
    "pinned_httpx_get_args",
    "safe_pinned_httpx_get",
    "safe_pinned_httpx_stream",
]
