import operator
from functools import reduce
from typing import TypeAlias

from unique_toolkit import LanguageModelService

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
from unique_web_search.services.search_engine.custom_api import (
    CustomAPI,
    CustomAPIConfig,
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
from unique_web_search.services.search_engine.utils.bing import (
    JsonConversionStrategy,
    LLMParserStrategy,
)
from unique_web_search.services.search_engine.vertexai import (
    VertexAI,
    VertexAIConfig,
)

SearchEngineTypes = (
    GoogleSearch
    | BingSearch
    | CustomAPI
    | JinaSearch
    | TavilySearch
    | BraveSearch
    | FireCrawlSearch
    | VertexAI
)
SearchEngineConfigTypes = (
    GoogleConfig
    | BingSearchConfig
    | CustomAPIConfig
    | JinaConfig
    | TavilyConfig
    | BraveSearchConfig
    | FireCrawlConfig
    | VertexAIConfig
)

ENGINE_NAME_TO_CONFIG = {
    "google": GoogleConfig,
    "jina": JinaConfig,
    "tavily": TavilyConfig,
    "bing": BingSearchConfig,
    "brave": BraveSearchConfig,
    "firecrawl": FireCrawlConfig,
    "vertexai": VertexAIConfig,
    "custom_api": CustomAPIConfig,
}


def get_search_engine_service(
    search_engine_config: SearchEngineConfigTypes,
    language_model_service: LanguageModelService,
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
            response_parsers = [
                JsonConversionStrategy(),
                LLMParserStrategy(
                    search_engine_config.language_model,
                    language_model_service,
                ),
            ]
            return BingSearch(search_engine_config, response_parsers)
        case SearchEngineType.BRAVE:
            return BraveSearch(search_engine_config)
        case SearchEngineType.VERTEXAI:
            return VertexAI(search_engine_config)
        case SearchEngineType.CUSTOM_API:
            return CustomAPI(search_engine_config)


def get_search_engine_config_types_from_names(engine_names: list[str]) -> TypeAlias:
    assert len(engine_names) >= 1, "At least one search engine must be active"

    selected_types = [
        ENGINE_NAME_TO_CONFIG[name.lower()]
        for name in engine_names
        if name.lower() in ENGINE_NAME_TO_CONFIG
    ]
    if not selected_types:
        raise ValueError(f"No search engine config found for names: {engine_names}")
    if len(selected_types) == 1:
        return selected_types[0]
    # Use reduce to create Union[Type1, Type2, Type3, ...]
    return reduce(operator.or_, selected_types)


def get_default_search_engine_config(
    engine_names: list[str],
) -> SearchEngineConfigTypes:
    assert len(engine_names) >= 1, "At least one search engine must be active"

    return ENGINE_NAME_TO_CONFIG[engine_names[0]]


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
    "get_search_engine_config_types_from_names",
    "get_default_search_engine_config",
    "VertexAIConfig",
    "VertexAI",
]
