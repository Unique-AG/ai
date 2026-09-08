from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from urllib.parse import urljoin

import httpx

from unique_search_proxy_core.url_safety.models import (
    BlockedCrawlTarget,
    CrawlTargetValidationError,
)
from unique_search_proxy_core.url_safety.netloc import extract_hostname
from unique_search_proxy_core.url_safety.settings import url_safety_settings

_LOGGER = logging.getLogger(__name__)

_REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})

# Browser-like UA avoids CDN bot stalls (e.g. Akamai) that make fail-closed
# redirect probing falsely block legitimate public pages.
_REDIRECT_PROBE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

ValidateUrlFn = Callable[[str], Awaitable[tuple[str, str] | None]]


async def resolve_redirect_chain(
    url: str,
    validate_url: ValidateUrlFn,
    *,
    http_client: httpx.AsyncClient | None = None,
) -> str:
    """Follow HTTP 3xx redirects hop-by-hop, validating each destination.

    Returns the final validated URL.
    Raises CrawlTargetValidationError if any hop is blocked or redirect probing
    cannot be completed (fail-closed to prevent GET-time redirect SSRF bypass).
    """
    if http_client is not None:
        return await _resolve_redirect_chain_with_client(
            url,
            validate_url,
            http_client,
        )

    async with httpx.AsyncClient() as client:
        return await _resolve_redirect_chain_with_client(
            url,
            validate_url,
            client,
        )


async def _resolve_redirect_chain_with_client(
    url: str,
    validate_url: ValidateUrlFn,
    client: httpx.AsyncClient,
) -> str:
    """Resolve redirects with a caller-owned client."""
    current = url
    timeout = url_safety_settings.redirect_timeout_seconds
    for _ in range(url_safety_settings.max_redirect_hops):
        error = await validate_url(current)
        if error is not None:
            category, reason = error
            raise CrawlTargetValidationError(
                [
                    BlockedCrawlTarget(
                        hostname=extract_hostname(current),
                        category=category,
                        reason=reason,
                    )
                ]
            )

        try:
            resp = await client.head(
                current,
                follow_redirects=False,
                headers={"User-Agent": _REDIRECT_PROBE_USER_AGENT},
                timeout=timeout,
            )
        except Exception as exc:
            _LOGGER.debug(
                "Redirect resolution blocked at %s due to network error: %s",
                current,
                exc,
            )
            raise CrawlTargetValidationError(
                [
                    BlockedCrawlTarget(
                        hostname=extract_hostname(current),
                        category="redirect",
                        reason=(
                            "Unable to verify redirect chain before crawl; "
                            "blocking to prevent redirect-based SSRF"
                        ),
                    )
                ]
            ) from exc

        if resp.status_code not in _REDIRECT_STATUS_CODES:
            break

        location = resp.headers.get("location")
        if not location:
            break

        current = urljoin(current, location)

    error = await validate_url(current)
    if error is not None:
        category, reason = error
        raise CrawlTargetValidationError(
            [
                BlockedCrawlTarget(
                    hostname=extract_hostname(current),
                    category=category,
                    reason=reason,
                )
            ]
        )

    return current
