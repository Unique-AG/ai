from abc import ABC, abstractmethod
from enum import StrEnum
from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from unique_toolkit.agentic.tools.config import get_configuration_dict

from unique_web_search.services.proxy.bridge import search_proxy_client_enabled
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)


class SearchEngineMode(StrEnum):
    STANDARD = "standard"
    AGENT = "agent"


class SearchEngineType(StrEnum):
    GOOGLE = "Google"
    JINA = "Jina"
    FIRECRAWL = "Firecrawl"
    TAVILY = "Tavily"
    BRAVE = "Brave"
    PERPLEXITY = "Perplexity"
    BING = "Bing"
    DUCKDUCKGO = "DuckDuckGo"
    VERTEXAI = "VertexAI"
    CUSTOM_API = "CustomAPI"


_SEARCH_ENGINE_MODE_MAP: dict[SearchEngineType, SearchEngineMode] = {
    SearchEngineType.GOOGLE: SearchEngineMode.STANDARD,
    SearchEngineType.JINA: SearchEngineMode.STANDARD,
    SearchEngineType.FIRECRAWL: SearchEngineMode.STANDARD,
    SearchEngineType.TAVILY: SearchEngineMode.STANDARD,
    SearchEngineType.BRAVE: SearchEngineMode.STANDARD,
    SearchEngineType.PERPLEXITY: SearchEngineMode.STANDARD,
    SearchEngineType.DUCKDUCKGO: SearchEngineMode.STANDARD,
    SearchEngineType.BING: SearchEngineMode.AGENT,
    SearchEngineType.VERTEXAI: SearchEngineMode.AGENT,
}


def get_search_engine_mode(
    engine_type: SearchEngineType,
    *,
    override: SearchEngineMode | None = None,
) -> SearchEngineMode:
    """Return the mode (standard vs agent) for a given search engine type.

    Args:
        engine_type: The search engine type to look up.
        override: If provided, returned as-is (used by CustomAPI with a
            user-configured mode).
    """
    if override is not None:
        return override
    return _SEARCH_ENGINE_MODE_MAP.get(engine_type, SearchEngineMode.STANDARD)


_SearchEngineExposedName = {
    SearchEngineType.GOOGLE: "Google Search",
    SearchEngineType.JINA: "Jina Search",
    SearchEngineType.FIRECRAWL: "Firecrawl Search",
    SearchEngineType.TAVILY: "Tavily Search",
    SearchEngineType.BRAVE: "Brave Search",
    SearchEngineType.PERPLEXITY: "Perplexity Search",
    SearchEngineType.BING: "Grounding with Bing",
    SearchEngineType.DUCKDUCKGO: "DuckDuckGo Search",
    SearchEngineType.VERTEXAI: "Grounding with VertexAI",
    SearchEngineType.CUSTOM_API: "Customized API Search",
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
        _legacy_search: Direct search implementation (no proxy).
        requires_scraping: Whether the search engine requires scraping.

    Subclasses with proxy support set ``supports_proxy_search = True`` and
    implement ``_proxy_search``.

    """

    supports_proxy_search: ClassVar[bool] = False

    def __init__(self, config: SearchEngineConfig):
        self.config = config

    @property
    @abstractmethod
    def requires_scraping(self) -> bool:
        """Whether the search engine requires scraping."""

    async def search(self, query: str, **kwargs) -> list[WebSearchResult]:
        """Search the web for the given query using the search engine."""
        if search_proxy_client_enabled and self.supports_proxy_search:
            return await self._proxy_search(query=query, **kwargs)
        return await self._legacy_search(query=query, **kwargs)

    @abstractmethod
    async def _proxy_search(self, query: str, **kwargs) -> list[WebSearchResult]:
        """Search the web via the search proxy."""

    @abstractmethod
    async def _legacy_search(self, query: str, **kwargs) -> list[WebSearchResult]:
        """Search the web directly without the search proxy."""
