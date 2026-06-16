"""HTTP client for ``POST /v1/crawl``."""

from __future__ import annotations

from typing import Any

from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.basic.schema import BasicCrawlRequest
from unique_search_proxy_core.crawlers.config_types import parse_crawl_request
from unique_search_proxy_core.crawlers.firecrawl.schema import FirecrawlCrawlRequest
from unique_search_proxy_core.crawlers.jina.schema import JinaCrawlRequest
from unique_search_proxy_core.crawlers.tavily.schema import TavilyCrawlRequest

from unique_search_proxy_sdk._endpoint import async_post_endpoint
from unique_search_proxy_sdk._generated.api.crawl import crawl_v1_crawl_post
from unique_search_proxy_sdk._generated.models.crawl_response import CrawlResponse
from unique_search_proxy_sdk._transport import OpenapiTransport
from unique_search_proxy_sdk._typed_endpoints import (
    BasicCrawlEndpoint,
    FirecrawlCrawlEndpoint,
    JinaCrawlEndpoint,
    TavilyCrawlEndpoint,
)
from unique_search_proxy_sdk.converters import to_sdk_crawl_request

_CRAWLER_ATTR_BY_VALUE: dict[str, str] = {
    CrawlerType.BASIC.value: "basic",
    CrawlerType.TAVILY.value: "tavily",
    CrawlerType.JINA.value: "jina",
    CrawlerType.FIRECRAWL.value: "firecrawl",
}


class CrawlClient:
    """Crawl URLs via flat, crawler-specific request bodies."""

    basic: BasicCrawlEndpoint
    tavily: TavilyCrawlEndpoint
    jina: JinaCrawlEndpoint
    firecrawl: FirecrawlCrawlEndpoint

    def __init__(self, transport: OpenapiTransport) -> None:
        self._transport = transport
        self.basic = BasicCrawlEndpoint(
            async_post_endpoint(
                transport,
                BasicCrawlRequest,
                parse=parse_crawl_request,
                to_sdk=to_sdk_crawl_request,
                post=crawl_v1_crawl_post.asyncio_detailed,
                response_type=CrawlResponse,
            ),
        )
        self.tavily = TavilyCrawlEndpoint(
            async_post_endpoint(
                transport,
                TavilyCrawlRequest,
                parse=parse_crawl_request,
                to_sdk=to_sdk_crawl_request,
                post=crawl_v1_crawl_post.asyncio_detailed,
                response_type=CrawlResponse,
            ),
        )
        self.jina = JinaCrawlEndpoint(
            async_post_endpoint(
                transport,
                JinaCrawlRequest,
                parse=parse_crawl_request,
                to_sdk=to_sdk_crawl_request,
                post=crawl_v1_crawl_post.asyncio_detailed,
                response_type=CrawlResponse,
            ),
        )
        self.firecrawl = FirecrawlCrawlEndpoint(
            async_post_endpoint(
                transport,
                FirecrawlCrawlRequest,
                parse=parse_crawl_request,
                to_sdk=to_sdk_crawl_request,
                post=crawl_v1_crawl_post.asyncio_detailed,
                response_type=CrawlResponse,
            ),
        )

    async def crawl(
        self,
        urls: list[str],
        *,
        crawler: CrawlerType | str = CrawlerType.BASIC,
        **params: Any,
    ) -> CrawlResponse:
        """Crawl URLs with a flat body validated by core request models."""
        crawler_value = crawler.value if isinstance(crawler, CrawlerType) else crawler
        attr = _CRAWLER_ATTR_BY_VALUE.get(crawler_value)
        if attr is None:
            msg = (
                f"Unknown crawler {crawler_value!r}; "
                f"expected one of {sorted(_CRAWLER_ATTR_BY_VALUE)}"
            )
            raise ValueError(msg)
        provider = getattr(self, attr)
        return await provider(urls=urls, **params)


__all__ = ["CrawlClient"]
