from __future__ import annotations

import logging
from ipaddress import ip_address
from urllib.parse import urlsplit

from unique_search_proxy_core.url_safety import dns, redirect, resolver
from unique_search_proxy_core.url_safety.models import (
    BlockedCrawlTarget,
    CrawlTargetValidationError,
    ResolvedCrawlTarget,
    UrlSafetyOutcome,
    bypass_crawl_target,
)
from unique_search_proxy_core.url_safety.policy import validate_target_cheap
from unique_search_proxy_core.url_safety.settings import url_safety_settings

_LOGGER = logging.getLogger(__name__)


def _safe_hostname(url: str) -> str | None:
    """Extract the hostname from a URL without ever raising.

    ``urlsplit(...).hostname`` raises ``ValueError`` for malformed IPv6 hosts
    (e.g. ``http://[::1``). This must never happen on the fail-closed path,
    where a single bad URL would otherwise abort the whole batch.
    """
    try:
        return urlsplit(url).hostname
    except ValueError:
        return None


class UrlSafetyService:
    @staticmethod
    async def validate_urls_individually(urls: list[str]) -> list[UrlSafetyOutcome]:
        if not url_safety_settings.enabled:
            return [
                UrlSafetyOutcome(url=url, resolved=bypass_crawl_target(url))
                for url in urls
            ]

        outcomes: list[UrlSafetyOutcome] = []
        for url in urls:
            working_url = url.strip()
            try:
                if url_safety_settings.resolve_redirects:
                    working_url = await redirect.resolve_redirect_chain(
                        working_url,
                        validate_url=UrlSafetyService.validate_url,
                    )
                resolved = await resolver.resolve_crawl_target(working_url)
                outcomes.append(UrlSafetyOutcome(url=url, resolved=resolved))
            except CrawlTargetValidationError as exc:
                blocked = exc.blocked_targets[0]
                outcomes.append(UrlSafetyOutcome(url=url, blocked=blocked))
            except Exception:
                # Fail closed: an unexpected error while validating a single URL
                # must block only that URL, never fail the whole batch.
                _LOGGER.exception("URL safety validation failed unexpectedly")
                outcomes.append(
                    UrlSafetyOutcome(
                        url=url,
                        blocked=BlockedCrawlTarget(
                            hostname=_safe_hostname(working_url),
                            category="validation_error",
                            reason="URL safety validation failed unexpectedly",
                        ),
                    )
                )
        return outcomes

    @staticmethod
    async def validate_batch_urls(urls: list[str]) -> list[ResolvedCrawlTarget]:
        outcomes = await UrlSafetyService.validate_urls_individually(urls)
        blocked_targets = [
            outcome.blocked for outcome in outcomes if outcome.blocked is not None
        ]
        if blocked_targets:
            raise CrawlTargetValidationError(blocked_targets)

        return [
            outcome.resolved for outcome in outcomes if outcome.resolved is not None
        ]

    @staticmethod
    async def validate_url(url: str) -> tuple[str, str] | None:
        """Full validation including async DNS check.

        Returns a ``(category, reason)`` tuple if the URL should be blocked, or
        ``None`` if it is allowed.
        """
        error = validate_target_cheap(url)
        if error is not None:
            return error

        hostname = urlsplit(url).hostname
        if hostname is None:
            return None

        normalized_host = hostname.rstrip(".").lower()
        try:
            ip_address(normalized_host)
            return None
        except ValueError:
            pass

        return await dns.validate_resolved_host(normalized_host)

    @staticmethod
    async def resolve_crawl_target(url: str) -> ResolvedCrawlTarget:
        return await resolver.resolve_crawl_target(url)
