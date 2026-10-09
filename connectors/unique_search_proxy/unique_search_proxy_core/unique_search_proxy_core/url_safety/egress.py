from __future__ import annotations

from collections.abc import Mapping
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
    if max_redirect_hops < 0:
        raise ValueError("max_redirect_hops must be non-negative")

    current_target = target
    for redirects_followed in range(max_redirect_hops + 1):
        request_url, pin_headers, extensions = pinned_httpx_get_args(current_target)
        response = await client.get(
            request_url,
            headers={**(headers or {}), **pin_headers},
            extensions=extensions or None,
            timeout=timeout,
            follow_redirects=False,
        )

        try:
            next_url = redirect_target_url(response, current_target.normalized_url)
            if next_url is not None:
                parsed_next_url = urlsplit(next_url)
                _ = parsed_next_url.hostname
                _ = parsed_next_url.port
        except ValueError as exc:
            raise CrawlTargetValidationError(
                [
                    BlockedCrawlTarget(
                        hostname=current_target.hostname or None,
                        category="redirect",
                        reason="Redirect target URL is missing or malformed",
                    )
                ]
            ) from exc
        if next_url is None:
            return response

        if redirects_followed == max_redirect_hops:
            raise CrawlTargetValidationError(
                [
                    BlockedCrawlTarget(
                        hostname=current_target.hostname or None,
                        category="redirect",
                        reason="Maximum redirect hop count exceeded",
                    )
                ]
            )

        current_target = (
            await resolve_crawl_target(next_url)
            if enforce_url_safety
            else bypass_crawl_target(next_url)
        )

    raise AssertionError("redirect loop must return or raise")


__all__ = ["pinned_httpx_get_args", "safe_pinned_httpx_get"]
