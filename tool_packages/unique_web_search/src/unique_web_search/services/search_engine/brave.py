import logging
from typing import Literal

from httpx import AsyncClient, Response
from pydantic import BaseModel

from unique_web_search.client_settings import get_brave_search_settings
from unique_web_search.services.search_engine import (
    BaseSearchEngineConfig,
    SearchEngine,
    SearchEngineType,
)
from unique_web_search.services.search_engine.base import get_search_engine_model_config
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
}

PAGINATION_SIZE = (
    20  # Brave Search API only supports a maximum of 20 results per request
)


def get_headers(api_key: str) -> dict[str, str]:
    return HEADERS.copy() | {"X-Subscription-Key": api_key}


class BraveSearchParameters(BaseModel):
    q: str
    count: int
    offset: int
    safesearch: Literal["strict", "moderate", "off"] = "strict"


class BraveSearchConfig(BaseSearchEngineConfig[SearchEngineType.BRAVE]):
    model_config = get_search_engine_model_config(SearchEngineType.BRAVE)
    search_engine_name: Literal[SearchEngineType.BRAVE] = SearchEngineType.BRAVE


class BraveSearch(SearchEngine[BraveSearchConfig]):
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.is_configured = get_brave_search_settings().is_configured

    @property
    def requires_scraping(self) -> bool:
        return True

    async def search(self, query: str, **kwargs) -> list[WebSearchResult]:
        search_results = []
        fetch_size = self.config.fetch_size

        for start_index in range(0, fetch_size, PAGINATION_SIZE):
            effective_num_fetch = min(fetch_size - start_index, PAGINATION_SIZE)
            params = BraveSearchParameters(
                q=query, count=effective_num_fetch, offset=start_index
            )

            response = await self._perform_web_search_request(params=params)
            search_results.extend(self._extract_urls(response.json()))

        return search_results

    async def _perform_web_search_request(
        self, params: BraveSearchParameters
    ) -> Response:
        """Send a request to the search engine.

        Args:
            query: The query.
            start_index: The start index.

        Returns:
            list[dict]: The search results.

        """
        api_endpoint = get_brave_search_settings().api_endpoint
        api_key = get_brave_search_settings().api_key
        assert api_key is not None and api_endpoint is not None

        async with AsyncClient() as client:
            response = await client.get(
                api_endpoint,
                params=params.model_dump(exclude_none=True),
                headers=get_headers(api_key),
            )
        return response

    def _extract_urls(self, brave_response: dict) -> list[WebSearchResult]:
        search_results = []
        if "web" in brave_response and brave_response["web"] is not None:
            search_results.extend(brave_response["web"]["results"])
        if "news" in brave_response and brave_response["news"] is not None:
            search_results.extend(brave_response["news"]["results"])
        if not search_results:
            _LOGGER.warning("No search results found in Brave search response")
            return []

        return [
            WebSearchResult(
                url=item["url"],
                title=item["title"],
                snippet=self._safe_load_key(item, "description"),
            )
            for item in search_results
        ]

    @staticmethod
    def _safe_load_key(brave_response: dict, key: str, default: str = "") -> str:
        try:
            return brave_response[key]
        except KeyError:
            _LOGGER.warning(f"Key {key} not found in Brave search response")
            return default
