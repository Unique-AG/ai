import logging
from typing import Annotated, Literal, TypeVar, cast, override

from perplexity import AsyncPerplexity, Omit
from perplexity.types.search_create_response import Result
from pydantic import Field
from unique_search_proxy_core.search_engines.perplexity.schema import (
    PerplexityRecencyFilter,
)
from unique_toolkit._common.pydantic_helpers import DeactivatedNone

from unique_web_search.client_settings import get_perplexity_search_settings
from unique_web_search.services.client.proxy_config import async_client
from unique_web_search.services.proxy.bridge import (
    open_search_proxy_client,
    search_proxy_client_enabled,
)
from unique_web_search.services.proxy.mappers import map_search_response
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
    supports_proxy_search = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_configured = (
            search_proxy_client_enabled
            or get_perplexity_search_settings().is_configured
        )

    @property
    def requires_scraping(self) -> bool:
        return self.config.requires_scraping

    @override
    async def _proxy_search(self, query: str, **kwargs) -> list[WebSearchResult]:
        async with open_search_proxy_client(timeout=30.0) as client:
            response = await client.search.perplexity(
                query=query,
                fetch_size=min(self.config.fetch_size, MAX_RESULTS_PER_REQUEST),
                country=self.config.country,
                max_tokens=self.config.max_tokens,
                search_recency_filter=cast(
                    PerplexityRecencyFilter | None,
                    self.config.search_recency_filter,
                ),
            )
            return map_search_response(response)

    @override
    async def _legacy_search(self, query: str, **kwargs) -> list[WebSearchResult]:
        settings = get_perplexity_search_settings()
        assert settings.is_configured

        max_results = min(self.config.fetch_size, MAX_RESULTS_PER_REQUEST)

        async with async_client() as http_client:
            perplexity_client = AsyncPerplexity(
                api_key=settings.api_key, http_client=http_client
            )
            response = await perplexity_client.search.create(
                query=query,
                max_results=max_results,
                country=_return_omit_if_none(self.config.country),
                max_tokens=_return_omit_if_none(self.config.max_tokens),
                search_mode=_return_omit_if_none(self.config.search_mode),
                search_recency_filter=_return_omit_if_none(
                    self.config.search_recency_filter
                ),
                search_type=_return_omit_if_none(self.config.search_type),
            )

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


T = TypeVar("T")


def _return_omit_if_none(value: T | None) -> T | Omit:
    if value is None:
        return Omit()
    else:
        return value
