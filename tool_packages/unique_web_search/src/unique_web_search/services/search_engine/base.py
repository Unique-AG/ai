from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from unique_toolkit.agentic.tools.config import get_configuration_dict

from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)


class SearchEngineType(StrEnum):
    GOOGLE = "Google"
    JINA = "Jina"
    FIRECRAWL = "Firecrawl"
    TAVILY = "Tavily"
    BRAVE = "Brave"
    BING = "Bing"
    DUCKDUCKGO = "DuckDuckGo"
    VERTEXAI = "VertexAI"
    CUSTOM_API = "CustomAPI"


_SearchEngineExposedName = {
    SearchEngineType.GOOGLE: "Google Search Engine",
    SearchEngineType.JINA: "Jina Search",
    SearchEngineType.FIRECRAWL: "Firecrawl Search",
    SearchEngineType.TAVILY: "Tavily Search",
    SearchEngineType.BRAVE: "Brave Search Engine",
    SearchEngineType.BING: "Grounding with Bing",
    SearchEngineType.DUCKDUCKGO: "DuckDuckGo Search Engine",
    SearchEngineType.VERTEXAI: "VertexAI Search Engine",
    SearchEngineType.CUSTOM_API: "Customized API Search Engine",
}


def get_search_engine_model_config(
    search_engine_name: SearchEngineType,
) -> ConfigDict:
    return get_configuration_dict(
        title=_SearchEngineExposedName.get(
            search_engine_name, "Undefined Search Engine"
        )
    )


T = TypeVar("T", bound=SearchEngineType)


class BaseSearchEngineConfig(BaseModel, Generic[T]):
    model_config = get_configuration_dict()
    search_engine_name: T
    fetch_size: int = Field(
        default=5,
        description="Number of search results to fetch",
    )


SearchEngineConfig = TypeVar(
    "SearchEngineConfig",
    bound=BaseSearchEngineConfig,
)


class SearchEngine(ABC, Generic[SearchEngineConfig]):
    """Base class for the search engine. It provides the common methods to search the web. This allows to use different search engines easily.

    Abstract Methods:
        _extract_urls: Clean the response from the search engine.
        _get_request_params: Get the request parameters.
        requires_scraping: Whether the search engine requires scraping.

    Args:
        assistant: The assistant configuration.
        chat_manager: The chat manager.

    """

    def __init__(self, config: SearchEngineConfig):
        self.config = config

    @property
    @abstractmethod
    def requires_scraping(self) -> bool:
        """Whether the search engine requires scraping."""

    @abstractmethod
    async def search(self, query: str, **kwargs) -> list[WebSearchResult]:
        """Search the web for the given query using the search engine."""
