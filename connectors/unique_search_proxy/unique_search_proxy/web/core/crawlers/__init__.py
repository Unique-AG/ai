from unique_search_proxy.web.core.crawlers.base import (
    BaseCrawler,
    BaseCrawlerConfig,
    CrawlerType,
)
from unique_search_proxy.web.core.crawlers.basic import (
    BasicCrawlerCall,
    BasicCrawlerConfig,
    BasicCrawlerService,
)
from unique_search_proxy.web.core.crawlers.config_types import (
    CRAWLER_NAME_TO_CONFIG,
    CrawlerConfigTypes,
    parse_crawler_config,
)


def register_builtin_crawlers() -> None:
    from unique_search_proxy.web.core.registry import register_crawler

    register_crawler(
        CrawlerType.BASIC.value,
        BasicCrawlerService,
        config_model=BasicCrawlerConfig,
    )


__all__ = [
    "BaseCrawler",
    "BaseCrawlerConfig",
    "BasicCrawlerCall",
    "BasicCrawlerConfig",
    "BasicCrawlerService",
    "CRAWLER_NAME_TO_CONFIG",
    "CrawlerConfigTypes",
    "CrawlerType",
    "parse_crawler_config",
    "register_builtin_crawlers",
]
