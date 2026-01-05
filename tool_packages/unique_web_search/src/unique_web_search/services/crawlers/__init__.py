import operator
from functools import reduce
from typing import TypeAlias

from unique_web_search.services.crawlers.base import (
    CrawlerType,
)
from unique_web_search.services.crawlers.basic import (
    BasicCrawler,
    BasicCrawlerConfig,
)
from unique_web_search.services.crawlers.crawl4ai import (
    Crawl4AiCrawler,
    Crawl4AiCrawlerConfig,
)
from unique_web_search.services.crawlers.firecrawl import (
    FirecrawlCrawler,
    FirecrawlCrawlerConfig,
)
from unique_web_search.services.crawlers.jina import (
    JinaCrawler,
    JinaCrawlerConfig,
)
from unique_web_search.services.crawlers.tavily import (
    TavilyCrawler,
    TavilyCrawlerConfig,
)

CrawlerTypes = (
    BasicCrawler | Crawl4AiCrawler | FirecrawlCrawler | JinaCrawler | TavilyCrawler
)

CrawlerConfigTypes = (
    BasicCrawlerConfig
    | Crawl4AiCrawlerConfig
    | FirecrawlCrawlerConfig
    | JinaCrawlerConfig
    | TavilyCrawlerConfig
)

CRAWLER_NAME_TO_CONFIG = {
    "basic": BasicCrawlerConfig,
    "crawl4ai": Crawl4AiCrawlerConfig,
    "firecrawl": FirecrawlCrawlerConfig,
    "jina": JinaCrawlerConfig,
    "tavily": TavilyCrawlerConfig,
}


def get_crawler_service(
    crawler_config: CrawlerConfigTypes,
):
    match crawler_config.crawler_type:
        case CrawlerType.BASIC:
            return BasicCrawler(crawler_config)
        case CrawlerType.CRAWL4AI:
            return Crawl4AiCrawler(crawler_config)
        case CrawlerType.TAVILY:
            return TavilyCrawler(crawler_config)
        case CrawlerType.FIRECRAWL:
            return FirecrawlCrawler(crawler_config)
        case CrawlerType.JINA:
            return JinaCrawler(crawler_config)


def get_crawler_config_types_from_names(crawler_names: list[str]) -> TypeAlias:
    assert len(crawler_names) >= 1, "At least one crawler must be active"

    selected_types = [
        CRAWLER_NAME_TO_CONFIG[name.lower()]
        for name in crawler_names
        if name.lower() in CRAWLER_NAME_TO_CONFIG
    ]
    if not selected_types:
        raise ValueError(f"No crawler config found for names: {crawler_names}")
    if len(selected_types) == 1:
        return selected_types[0]
    # Use reduce to create Union[Type1, Type2, Type3, ...]
    return reduce(operator.or_, selected_types)


def get_default_crawler_config(
    crawler_names: list[str],
) -> CrawlerConfigTypes:
    assert len(crawler_names) >= 1, "At least one crawler must be active"

    return CRAWLER_NAME_TO_CONFIG[crawler_names[0]]


__all__ = [
    "BasicCrawler",
    "BasicCrawlerConfig",
    "Crawl4AiCrawler",
    "Crawl4AiCrawlerConfig",
    "FirecrawlCrawler",
    "FirecrawlCrawlerConfig",
    "JinaCrawler",
    "JinaCrawlerConfig",
    "TavilyCrawler",
    "TavilyCrawlerConfig",
    "CrawlerType",
    "get_crawler_service",
    "CrawlerConfigTypes",
    "CrawlerTypes",
    "get_crawler_config_types_from_names",
    "get_default_crawler_config",
]
