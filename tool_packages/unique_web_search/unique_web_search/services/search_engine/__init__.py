from unique_web_search.services.search_engine.base import (
    SearchEngineType,
)
from unique_web_search.services.search_engine.firecrawl import (
    FireCrawlConfig,
    FireCrawlSearch,
)
from unique_web_search.services.search_engine.google import (
    GoogleConfig,
    GoogleSearch,
)
from unique_web_search.services.search_engine.jina import (
    JinaConfig,
    JinaSearch,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)
from unique_web_search.services.search_engine.tavily import (
    TavilyConfig,
    TavilySearch,
)

SearchEngineTypes = FireCrawlSearch | GoogleSearch | JinaSearch | TavilySearch
SearchEngineConfigTypes = FireCrawlConfig | GoogleConfig | JinaConfig | TavilyConfig


def get_search_engine_service(
    search_engine_config: SearchEngineConfigTypes,
):
    match search_engine_config.search_engine_name:
        case SearchEngineType.FIRECRAWL:
            return FireCrawlSearch(search_engine_config)
        case SearchEngineType.GOOGLE:
            return GoogleSearch(search_engine_config)
        case SearchEngineType.JINA:
            return JinaSearch(search_engine_config)
        case SearchEngineType.TAVILY:
            return TavilySearch(search_engine_config)


__all__ = [
    "SearchEngineType",
    "FireCrawlConfig",
    "FireCrawlSearch",
    "GoogleConfig",
    "GoogleSearch",
    "JinaConfig",
    "JinaSearch",
    "WebSearchResult",
    "TavilyConfig",
    "TavilySearch",
    "get_search_engine_service",
]
