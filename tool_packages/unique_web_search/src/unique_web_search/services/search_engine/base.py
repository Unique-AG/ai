from abc import ABC, abstractmethod
from enum import StrEnum
from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel

from unique_web_search.services.proxy.bridge import search_proxy_client_enabled
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)


class SearchEngineMode(StrEnum):
    STANDARD = "standard"
    AGENT = "agent"


class LocalSearchEngineType(StrEnum):
    CUSTOM_API = "custom_api"


SearchEngineConfig = TypeVar(
    "SearchEngineConfig",
    bound=BaseModel,
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
    def requires_scraping(self) -> bool:
        """Whether the search engine requires scraping."""
        return False

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
