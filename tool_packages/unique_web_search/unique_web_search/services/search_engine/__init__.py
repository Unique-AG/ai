from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI

from unique_web_search.services.search_engine.base import (
    BaseSearchEngineConfig,
    SearchEngine,
    SearchEngineType,
)
from unique_web_search.services.search_engine.bing import (
    BingSearch,
    BingSearchConfig,
)
from unique_web_search.services.search_engine.brave import (
    BraveSearch,
    BraveSearchConfig,
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
from unique_web_search.services.search_engine.tavily import (
    TavilyConfig,
    TavilySearch,
)

SearchEngineTypes = (
    GoogleSearch
    | JinaSearch
    | TavilySearch
    | BingSearch
    | BraveSearch
    | FireCrawlSearch
)
SearchEngineConfigTypes = (
    GoogleConfig
    | JinaConfig
    | TavilyConfig
    | BingSearchConfig
    | BraveSearchConfig
    | FireCrawlConfig
)


def get_search_engine_service(
    search_engine_config: SearchEngineConfigTypes,
    language_model_service: LanguageModelService,
    lmi: LMI,
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
        case SearchEngineType.BING:
            return BingSearch(search_engine_config, language_model_service, lmi)
        case SearchEngineType.BRAVE:
            return BraveSearch(search_engine_config, language_model_service, lmi)


__all__ = [
    "SearchEngineType",
    "FireCrawlConfig",
    "FireCrawlSearch",
    "GoogleConfig",
    "GoogleSearch",
    "JinaConfig",
    "JinaSearch",
    "TavilyConfig",
    "TavilySearch",
    "BingSearchConfig",
    "BingSearch",
    "BraveSearch",
    "BraveSearchConfig",
    "get_search_engine_service",
    "BaseSearchEngineConfig",
    "SearchEngine",
    "SearchEngineType",
]
