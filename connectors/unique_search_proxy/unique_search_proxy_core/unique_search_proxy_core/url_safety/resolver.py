from __future__ import annotations

import asyncio
from ipaddress import ip_address
from urllib.parse import urlsplit

from unique_search_proxy_core.url_safety import dns
from unique_search_proxy_core.url_safety.models import (
    BlockedCrawlTarget,
    CrawlTargetValidationError,
    ResolvedCrawlTarget,
)
from unique_search_proxy_core.url_safety.netloc import extract_hostname
from unique_search_proxy_core.url_safety.policy import validate_target_cheap


async def resolve_crawl_target(url: str) -> ResolvedCrawlTarget:
    """Validate and resolve a single URL, performing DNS exactly once."""
    normalized_url = url.strip()

    validation_error = validate_target_cheap(normalized_url)
    if validation_error is not None:
        category, reason = validation_error
        raise CrawlTargetValidationError(
            [
                BlockedCrawlTarget(
                    hostname=extract_hostname(normalized_url),
                    category=category,
                    reason=reason,
                )
            ]
        )

    parsed_url = urlsplit(normalized_url)
    hostname = parsed_url.hostname
    if hostname is None:
        raise CrawlTargetValidationError(
            [
                BlockedCrawlTarget(
                    hostname=None,
                    category="host",
                    reason="URL host is missing or malformed",
                )
            ]
        )

    normalized_host = hostname.rstrip(".").lower()

    try:
        target_ip = ip_address(normalized_host)
    except ValueError:
        resolved_addresses, validation_error = await dns.resolve_and_validate_host(
            normalized_host
        )
        if validation_error is not None:
            category, reason = validation_error
            raise CrawlTargetValidationError(
                [
                    BlockedCrawlTarget(
                        hostname=normalized_host,
                        category=category,
                        reason=reason,
                    )
                ]
            )
        return ResolvedCrawlTarget(
            normalized_url=normalized_url,
            hostname=normalized_host,
            resolved_ip=resolved_addresses[0],
            used_dns_resolution=True,
        )

    return ResolvedCrawlTarget(
        normalized_url=normalized_url,
        hostname=normalized_host,
        resolved_ip=str(target_ip),
        used_dns_resolution=False,
    )


async def resolve_crawl_targets_batch(urls: list[str]) -> list[ResolvedCrawlTarget]:
    """Resolve and validate each URL, collecting all policy violations before raising."""
    results: list[ResolvedCrawlTarget | BaseException] = list(
        await asyncio.gather(
            *[resolve_crawl_target(url) for url in urls],
            return_exceptions=True,
        )
    )

    blocked: list[BlockedCrawlTarget] = []
    resolved: list[ResolvedCrawlTarget] = []
    for result in results:
        if isinstance(result, CrawlTargetValidationError):
            blocked.extend(result.blocked_targets)
        elif isinstance(result, BaseException):
            raise result
        else:
            resolved.append(result)

    if blocked:
        raise CrawlTargetValidationError(blocked)

    return resolved
