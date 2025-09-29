from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel
from unique_toolkit.agentic.tools.config import (
    get_configuration_dict,
)

from unique_web_search.services.helpers import (
    clean_model_title_generator,
    experimental_model_title_generator,
)


class CrawlerType(StrEnum):
    CRAWL4AI = "Crawl4AiCrawler"
    BASIC = "BasicCrawler"
    NO_CRAWLER = "NoCrawler"
    TAVILY = "TavilyCrawler"
    FIRECRAWL = "FirecrawlCrawler"
    JINA = "JinaCrawler"
    NONE = "None"


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
    def __init__(self, config: CrawlerConfig):
        self.config = config

    @abstractmethod
    async def crawl(self, urls: list[str]) -> list[str]: ...
