from pydantic import BaseModel
from unique_search_proxy_core.crawlers import CrawlerType
from unique_search_proxy_core.crawlers.firecrawl.schema import FirecrawlConfig
from unique_search_proxy_core.crawlers.jina.schema import JinaConfig
from unique_search_proxy_core.crawlers.tavily.schema import TavilyConfig

from unique_web_search.services.crawlers.base import BaseCrawler
from unique_web_search.services.crawlers.registry import (
    CRAWLER_REGISTRY,
    get_crawler_service,
)

CRAWLER_REGISTRY.autodiscover(
    __path__,
    __name__,
    exclude=frozenset({"url_safety", "utils", "registry"}),
)

from unique_web_search.services.crawlers.basic import (  # noqa: E402
    BasicConfig,
    BasicCrawler,
)
from unique_web_search.services.crawlers.firecrawl import (  # noqa: E402
    FirecrawlCrawler,
)
from unique_web_search.services.crawlers.jina import JinaCrawler  # noqa: E402
from unique_web_search.services.crawlers.tavily import TavilyCrawler  # noqa: E402

CrawlerTypes = BasicCrawler | FirecrawlCrawler | JinaCrawler | TavilyCrawler

CrawlerConfigTypes = BasicConfig | FirecrawlConfig | JinaConfig | TavilyConfig

CRAWLER_NAME_TO_CONFIG = CRAWLER_REGISTRY.name_to_config()


def get_crawler_config_types_from_names(crawler_names: list[str]) -> type[BaseModel]:
    return CRAWLER_REGISTRY.config_types_from_names(crawler_names)


def get_default_crawler_config(crawler_names: list[str]) -> type[BaseModel]:
    return CRAWLER_REGISTRY.default_config(crawler_names)


__all__ = [
    "BasicCrawler",
    "BasicConfig",
    "FirecrawlCrawler",
    "FirecrawlConfig",
    "JinaCrawler",
    "JinaConfig",
    "TavilyCrawler",
    "TavilyConfig",
    "CrawlerType",
    "BaseCrawler",
    "get_crawler_service",
    "CrawlerConfigTypes",
    "CrawlerTypes",
    "get_crawler_config_types_from_names",
    "get_default_crawler_config",
]
