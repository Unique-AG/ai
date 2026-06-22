from abc import ABC, abstractmethod
from enum import StrEnum
from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel
from unique_search_proxy_core.url_safety import (
    CrawlTargetValidationError,
    ResolvedCrawlTarget,
    UrlSafetyService,
)
from unique_toolkit.agentic.tools.config import (
    get_configuration_dict,
)

from unique_web_search.metrics import crawl_blocked
from unique_web_search.services.helpers import (
    clean_model_title_generator,
    experimental_model_title_generator,
)
from unique_web_search.services.proxy.bridge import search_proxy_client_enabled


class CrawlerType(StrEnum):
    CRAWL4AI = "Crawl4AiCrawler"
    BASIC = "BasicCrawler"
    NO_CRAWLER = "NoCrawler"
    TAVILY = "TavilyCrawler"
    FIRECRAWL = "FirecrawlCrawler"
    JINA = "JinaCrawler"


T = TypeVar("T", bound=CrawlerType)


class BaseCrawlerConfig(BaseModel, Generic[T]):
    model_config = get_configuration_dict(
        model_title_generator=clean_model_title_generator
    )
    crawler_type: T
    timeout: int = 10


class BaseCrawlerConfigExperimental(BaseCrawlerConfig[T]):
    model_config = get_configuration_dict(
        model_title_generator=experimental_model_title_generator
    )


CrawlerConfig = TypeVar(
    "CrawlerConfig",
    bound=BaseCrawlerConfig,
)


class BaseCrawler(ABC, Generic[CrawlerConfig]):
    supports_proxy_crawl: ClassVar[bool] = False

    def __init__(self, config: CrawlerConfig):
        self.config = config

    async def crawl(self, urls: list[str]) -> list[str]:
        if search_proxy_client_enabled and self.supports_proxy_crawl:
            return await self._proxy_crawl(urls)

        try:
            targets = await UrlSafetyService.validate_batch_urls(urls)
        except CrawlTargetValidationError as exc:
            for target in exc.blocked_targets:
                crawl_blocked.labels(reason_category=target.category).inc()
            raise
        return await self._legacy_crawl(targets)

    @abstractmethod
    async def _proxy_crawl(self, urls: list[str]) -> list[str]: ...

    @abstractmethod
    async def _legacy_crawl(self, targets: list[ResolvedCrawlTarget]) -> list[str]: ...
