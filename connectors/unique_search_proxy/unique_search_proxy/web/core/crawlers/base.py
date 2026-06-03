from __future__ import annotations

from abc import ABC, abstractmethod

from unique_search_proxy.web.core.crawlers.url_safety import (
    ResolvedCrawlTarget,
    UrlSafetyService,
)
from unique_search_proxy.web.core.schema import CrawlerConfig


class BaseCrawler(ABC):
    """Crawler contract: url safety validation runs before provider fetch."""

    crawler_id: str

    def __init__(self, config: CrawlerConfig) -> None:
        self.config = config

    async def crawl(self, urls: list[str]) -> list[ResolvedCrawlTarget]:
        targets = await UrlSafetyService.validate_batch_urls(urls)
        await self._crawl(targets)
        return targets

    @abstractmethod
    async def _crawl(self, targets: list[ResolvedCrawlTarget]) -> None:
        """Provider-specific crawl implementation."""
