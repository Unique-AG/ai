from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.basic.schema import BasicCrawlerConfig

from unique_search_proxy_client.web.core.crawlers.basic.service import (
    BasicCrawlerService,
)


def register_builtin_crawlers() -> None:
    from unique_search_proxy_client.web.core.registry import register_crawler

    register_crawler(
        CrawlerType.BASIC.value,
        BasicCrawlerService,
        config_model=BasicCrawlerConfig,
    )


__all__ = [
    "BasicCrawlerConfig",
    "BasicCrawlerService",
    "CrawlerType",
    "register_builtin_crawlers",
]
