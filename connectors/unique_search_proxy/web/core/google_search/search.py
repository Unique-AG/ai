import logging
from typing import Literal
from httpx import AsyncClient
from core.google_search.schema import GoogleSearchQueryParams
from core.google_search.settings import GoogleSearchSettings
from pydantic import BaseModel, Field
from core.schema import (
    WebSearchResult,
    camelized_model_config,
    SearchRequest,
    SearchEngineType,
)
from httpx import Response
from core.google_search.exceptions import (
    GoogleSearchAPIKeyNotSetException,
    GoogleSearchAPIEndpointNotSetException,
    GoogleSearchEngineIDNotSetException,
)

_LOGGER = logging.getLogger(__name__)

# Pagingation size fixed to 10 because of the Google Search API limit
PAGINATION_SIZE = 10
MAX_TIMEOUT = 600


# Pydantic Models
class GoogleSearchParams(BaseModel):
    """Parameters for the Google Search engine."""

    model_config = camelized_model_config

    cx: str | None = Field(
        default=None,
        description="The Programmable Search Engine ID to use for this request",
    )
    fetch_size: int = Field(
        default=10, ge=1, le=100, description="The number of results to fetch"
    )


class GoogleSearchRequest(SearchRequest[SearchEngineType.GOOGLE, GoogleSearchParams]):
    """Request model for the Google Search engine."""

    model_config = camelized_model_config
    search_engine: Literal[SearchEngineType.GOOGLE] = SearchEngineType.GOOGLE
    params: GoogleSearchParams = Field(
        default_factory=GoogleSearchParams,
        description="Additional keyword arguments for the Google Search engine",
    )


class GoogleSearch:
    def __init__(self, params: GoogleSearchParams):
        google_search_settings = GoogleSearchSettings()
        self.fetch_size = params.fetch_size
        self.cx = params.cx or google_search_settings.engine_id

        if not google_search_settings.api_key:
            raise GoogleSearchAPIKeyNotSetException()
        if not google_search_settings.api_endpoint:
            raise GoogleSearchAPIEndpointNotSetException()
        if not self.cx:
            raise GoogleSearchEngineIDNotSetException()

        self.api_key = google_search_settings.api_key
        self.api_endpoint = google_search_settings.api_endpoint
        self.engine_id = self.cx

    async def search(self, query: str) -> list[WebSearchResult]:
        """Extract the URLs from the search results."""

        search_results = []
        start_index = 1
        fetch_size = self.fetch_size

        for start_index in range(1, fetch_size + 1, PAGINATION_SIZE):
            effective_num_fetch = min(fetch_size - start_index + 1, PAGINATION_SIZE)
            params = GoogleSearchQueryParams(
                q=query,
                cx=self.engine_id,
                key=self.api_key,
                start=start_index,
                num=effective_num_fetch,
            )
            async with AsyncClient(timeout=MAX_TIMEOUT) as client:
                response = await client.get(
                    self.api_endpoint, params=params.model_dump()
                )
                response.raise_for_status()
                results = _map_google_search_response_to_web_search_result(response)
                search_results.extend(results)

        return search_results


def _map_google_search_response_to_web_search_result(
    response: Response,
) -> list[WebSearchResult]:
    """Clean the response from the search engine."""
    results = response.json()
    return [
        WebSearchResult(
            url=item.get("link", "URL not available"),
            snippet=item.get("snippet", "Snippet not available"),
            title=item.get("title", item.get("htmlTitle", "Title not available")),
        )
        for item in results.get("items", [])
    ]
