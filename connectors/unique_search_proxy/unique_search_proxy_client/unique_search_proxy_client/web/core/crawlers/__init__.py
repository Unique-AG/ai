from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.basic.schema import BasicCrawlRequest
from unique_search_proxy_core.crawlers.firecrawl.schema import (
    FirecrawlCrawlRequest,
)
from unique_search_proxy_core.crawlers.jina.schema import JinaCrawlRequest
from unique_search_proxy_core.crawlers.tavily.schema import TavilyCrawlRequest

from unique_search_proxy_client.web.core.crawlers.basic.service import (
    BasicCrawlerService,
)
from unique_search_proxy_client.web.core.crawlers.firecrawl.service import (
    FirecrawlCrawlerService,
)
from unique_search_proxy_client.web.core.crawlers.jina.service import (
    JinaCrawlerService,
)
from unique_search_proxy_client.web.core.crawlers.tavily.service import (
    TavilyCrawlerService,
)


def register_builtin_crawlers() -> None:
    from unique_search_proxy_client.web.core.registry import register_crawler

    register_crawler(
        CrawlerType.BASIC.value,
        BasicCrawlerService,
        config_model=BasicCrawlRequest,
    )
    register_crawler(
        CrawlerType.TAVILY.value,
        TavilyCrawlerService,
        config_model=TavilyCrawlRequest,
    )
    register_crawler(
        CrawlerType.JINA.value,
        JinaCrawlerService,
        config_model=JinaCrawlRequest,
    )
    register_crawler(
        CrawlerType.FIRECRAWL.value,
        FirecrawlCrawlerService,
        config_model=FirecrawlCrawlRequest,
    )


__all__ = [
    "BasicCrawlRequest",
    "BasicCrawlerService",
    "CrawlerType",
    "FirecrawlCrawlRequest",
    "FirecrawlCrawlerService",
    "JinaCrawlRequest",
    "JinaCrawlerService",
    "TavilyCrawlRequest",
    "TavilyCrawlerService",
    "register_builtin_crawlers",
]
