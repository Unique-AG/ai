import logging
from typing import Annotated, Literal

from perplexity import AsyncPerplexity, Omit
from perplexity.types.search_create_response import Result
from pydantic import Field
from unique_toolkit._common.pydantic_helpers import DeactivatedNone

from unique_web_search.client_settings import get_perplexity_search_settings
from unique_web_search.services.client.proxy_config import async_client
from unique_web_search.services.search_engine import (
    BaseSearchEngineConfig,
    SearchEngine,
    SearchEngineType,
)
from unique_web_search.services.search_engine.base import get_search_engine_model_config
from unique_web_search.services.search_engine.schema import WebSearchResult

_LOGGER = logging.getLogger(__name__)

# Perplexity Search API allows 1–20 results per request.
MAX_RESULTS_PER_REQUEST = 20


class PerplexitySearchConfig(BaseSearchEngineConfig[SearchEngineType.PERPLEXITY]):
    model_config = get_search_engine_model_config(SearchEngineType.PERPLEXITY)
    search_engine_name: Literal[SearchEngineType.PERPLEXITY] = (
        SearchEngineType.PERPLEXITY
    )
    country: Annotated[str, Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        description="The country to use for the search. It's a two-letter country code.",
    )
    max_tokens: Annotated[int, Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        description="The maximum number of tokens to use for the context. It's a positive integer.",
    )
    search_mode: (
        Annotated[Literal["web", "academic", "sec"], Field(title="Active")]
        | DeactivatedNone
    ) = Field(
        default=None,
        description="The search mode to use for the search. It's a string.",
    )
    search_recency_filter: (
        Annotated[
            Literal["hour", "day", "week", "month", "year"], Field(title="Active")
        ]
        | DeactivatedNone
    ) = Field(
        default=None,
        description="The recency filter to use for the search. It's a string.",
    )
    search_type: (
        Annotated[Literal["web", "people"], Field(title="Active")] | DeactivatedNone
    ) = Field(
        default=None,
        description="The search type to use for the search. It's a string.",
    )

    requires_scraping: bool = False


class PerplexitySearch(SearchEngine[PerplexitySearchConfig]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_configured = get_perplexity_search_settings().is_configured

    @property
    def requires_scraping(self) -> bool:
        return self.config.requires_scraping

    async def search(self, query: str, **kwargs) -> list[WebSearchResult]:
        settings = get_perplexity_search_settings()
        assert settings.is_configured

        max_results = min(self.config.fetch_size, MAX_RESULTS_PER_REQUEST)
        client = AsyncPerplexity(api_key=settings.api_key, http_client=async_client())
        try:
            response = await client.search.create(
                query=query,
                max_results=max_results,
                country=self.config.country or Omit(),
                max_tokens=self.config.max_tokens or Omit(),
                search_mode=self.config.search_mode or Omit(),
                search_recency_filter=self.config.search_recency_filter or Omit(),
                search_type=self.config.search_type or Omit(),
            )
        finally:
            await client.close()

        return self._to_web_search_results(response.results)

    def _to_web_search_results(
        self, results: list[Result] | None
    ) -> list[WebSearchResult]:
        if not results:
            _LOGGER.warning("No search results found in Perplexity search response")
            return []

        return [
            WebSearchResult(
                url=result.url,
                title=result.title,
                snippet=result.snippet or "No Snippet Found",
            )
            for result in results
        ]
