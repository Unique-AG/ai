from unique_web_search.services.crawlers.base import (
    BaseCrawler,
    BaseCrawlerConfig,
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

DEFAULT_CRAWLER_CONFIG = BasicCrawlerConfig

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
    "BaseCrawler",
    "BaseCrawlerConfig",
    "get_crawler_service",
]
