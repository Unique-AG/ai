from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from unique_search_proxy_core.context import LOCAL_REQUEST_CONTEXT, RequestContext
from unique_search_proxy_core.crawlers.base import BaseCrawlerConfig
from unique_search_proxy_core.url_safety import (
    CrawlTargetValidationError,
    ResolvedCrawlTarget,
    UrlSafetyService,
)

from unique_web_search.metrics import crawl_blocked
from unique_web_search.services.proxy.bridge import (
    open_search_proxy_client,
    search_proxy_client_enabled,
)
from unique_web_search.services.proxy.mappers import map_crawl_response

CrawlerConfig = TypeVar(
    "CrawlerConfig",
    bound=BaseCrawlerConfig,
)


class BaseCrawler(ABC, Generic[CrawlerConfig]):
    """Base class for web-page crawlers.

    The search-proxy path is implemented entirely here. Subclasses only provide
    the direct ``_legacy_crawl`` implementation used when the proxy is disabled.
    """

    def __init__(
        self,
        config: CrawlerConfig,
        *,
        request_context: RequestContext = LOCAL_REQUEST_CONTEXT,
    ):
        self.config = config
        self._request_context = request_context

    async def crawl(self, urls: list[str]) -> list[str]:
        if search_proxy_client_enabled:
            return await self._proxy_crawl(urls)

        try:
            targets = await UrlSafetyService.validate_batch_urls(urls)
        except CrawlTargetValidationError as exc:
            for target in exc.blocked_targets:
                crawl_blocked.labels(reason_category=target.category).inc()
            raise
        return await self._legacy_crawl(targets)

    async def _proxy_crawl(self, urls: list[str]) -> list[str]:
        """Dump deployment config fields into the generic proxy crawl call."""
        params = self.config.model_dump(exclude={"crawler"}, exclude_none=True)
        async with open_search_proxy_client(
            timeout=float(self.config.timeout),
            context=self._request_context,
        ) as client:
            response = await client.crawl.crawl(
                urls=urls,
                crawler=self.config.crawler,
                **params,
            )
        return map_crawl_response(response, urls)

    @abstractmethod
    async def _legacy_crawl(self, targets: list[ResolvedCrawlTarget]) -> list[str]: ...
