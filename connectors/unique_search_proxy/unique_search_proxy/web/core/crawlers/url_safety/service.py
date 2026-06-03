from __future__ import annotations

import asyncio
from ipaddress import ip_address
from urllib.parse import urlsplit

from unique_search_proxy.web.core.crawlers.url_safety import dns, redirect, resolver
from unique_search_proxy.web.core.crawlers.url_safety.models import (
    ResolvedCrawlTarget,
    bypass_crawl_target,
)
from unique_search_proxy.web.core.crawlers.url_safety.policy import (
    validate_target_cheap,
)
from unique_search_proxy.web.core.crawlers.url_safety.settings import (
    url_safety_settings,
)


class UrlSafetyService:
    @staticmethod
    async def validate_batch_urls(urls: list[str]) -> list[ResolvedCrawlTarget]:
        if not url_safety_settings.enabled:
            return [bypass_crawl_target(url) for url in urls]

        working_urls = [url.strip() for url in urls]
        if url_safety_settings.resolve_redirects:
            working_urls = list(
                await asyncio.gather(
                    *[
                        redirect.resolve_redirect_chain(
                            u,
                            validate_url=UrlSafetyService.validate_url,
                        )
                        for u in working_urls
                    ]
                )
            )

        return await resolver.resolve_crawl_targets_batch(working_urls)

    @staticmethod
    async def validate_url(url: str) -> tuple[str, str] | None:
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
