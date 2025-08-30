from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel
from unique_toolkit.tools.config import get_configuration_dict


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
    model_config = get_configuration_dict()
    crawler_type: T
    timeout: int = 60


CrawlerConfig = TypeVar(
    "CrawlerConfig",
    bound=BaseCrawlerConfig,
)


class BaseCrawler(ABC, Generic[CrawlerConfig]):
    def __init__(self, config: CrawlerConfig):
        self.config = config

    @abstractmethod
    async def crawl(self, urls: list[str]) -> list[str]: ...
