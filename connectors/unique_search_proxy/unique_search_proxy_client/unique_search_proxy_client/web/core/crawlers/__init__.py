from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.basic.schema import (
    BasicConfig,
    BasicCrawlRequest,
)
from unique_search_proxy_core.crawlers.firecrawl.schema import (
    FirecrawlConfig,
    FirecrawlCrawlRequest,
)
from unique_search_proxy_core.crawlers.jina.schema import JinaConfig, JinaCrawlRequest
from unique_search_proxy_core.crawlers.tavily.schema import (
    TavilyConfig,
    TavilyCrawlRequest,
)

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
        config_model=BasicConfig,
    )
    register_crawler(
        CrawlerType.TAVILY.value,
        TavilyCrawlerService,
        config_model=TavilyConfig,
    )
    register_crawler(
        CrawlerType.JINA.value,
        JinaCrawlerService,
        config_model=JinaConfig,
    )
    register_crawler(
        CrawlerType.FIRECRAWL.value,
        FirecrawlCrawlerService,
        config_model=FirecrawlConfig,
    )


__all__ = [
    "BasicConfig",
    "BasicCrawlRequest",
    "BasicCrawlerService",
    "CrawlerType",
    "FirecrawlConfig",
    "FirecrawlCrawlRequest",
    "FirecrawlCrawlerService",
    "JinaConfig",
    "JinaCrawlRequest",
    "JinaCrawlerService",
    "TavilyConfig",
    "TavilyCrawlRequest",
    "TavilyCrawlerService",
    "register_builtin_crawlers",
]
