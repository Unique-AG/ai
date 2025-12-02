import logging

from httpx import AsyncClient
from core.google_search.schema import GoogleSearchQueryParams
from settings import env_settings
from pydantic import BaseModel
from core.schema import WebSearchResult, camelized_model_config
from core.google_search.helpers import map_google_search_response_to_web_search_result
from core.google_search.exceptions import (
    GoogleSearchAPIKeyNotSetException,
    GoogleSearchAPIEndpointNotSetException,
    GoogleSearchEngineIDNotSetException,
)

_LOGGER = logging.getLogger(__name__)

# Pagingation size fixed to 10 because of the Google Search API limit
PAGINATION_SIZE = 10


# Pydantic Models
class GoogleSearchParams(BaseModel):
    """Parameters for the Google Search engine."""

    model_config = camelized_model_config

    cx: str | None = None
    fetch_size: int = 10
    timeout: int = 10


class GoogleSearch:
    def __init__(self, params: GoogleSearchParams):
        self.fetch_size = params.fetch_size
        self.cx = params.cx or env_settings.google_search_engine_id
        self.timeout = params.timeout

        if not env_settings.google_search_api_key:
            raise GoogleSearchAPIKeyNotSetException()
        if not env_settings.google_search_api_endpoint:
            raise GoogleSearchAPIEndpointNotSetException()
        if not self.cx:
            raise GoogleSearchEngineIDNotSetException()

        self.api_key = env_settings.google_search_api_key
        self.api_endpoint = env_settings.google_search_api_endpoint
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
            async with AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.api_endpoint, params=params.model_dump()
                )
                response.raise_for_status()
                results = map_google_search_response_to_web_search_result(response)
                search_results.extend(results)

        return search_results
