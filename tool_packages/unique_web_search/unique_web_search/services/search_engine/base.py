import logging
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Generic, TypeVar

import tiktoken
from pydantic import BaseModel, Field

from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)


from unique_toolkit.tools.config import get_configuration_dict

ENCODER_MODEL = "cl100k_base"

encoder = tiktoken.get_encoding(ENCODER_MODEL)


logger = logging.getLogger(f"WebSearch.{__name__}")


class SearchEngineType(StrEnum):
    GOOGLE = "Google"
    JINA = "Jina"
    FIRECRAWL = "Firecrawl"
    TAVILY = "Tavily"


T = TypeVar("T", bound=SearchEngineType)


class BaseSearchEngineConfig(BaseModel, Generic[T]):
    model_config = get_configuration_dict()
    search_engine_name: T

    fetch_size: int = Field(
        default=15,
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
