import logging
from typing import Literal
from urllib.parse import urlparse

from httpx import AsyncClient, Response

from unique_web_search.client_settings import get_google_search_settings
from unique_web_search.services.search_engine import (
    BaseSearchEngineConfig,
    SearchEngine,
    SearchEngineType,
)
from unique_web_search.services.search_engine.google_utils.schema import (
    GoogleSearchOptionalQueryParams,
    GoogleSearchQueryParams,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)

logger = logging.getLogger(f"PythonAssistantCoreBundle.{__name__}")

# Pagingation size fixed to 10 because of the Google Search API limit
PAGINATION_SIZE = 10


class GoogleConfig(BaseSearchEngineConfig[SearchEngineType.GOOGLE]):
    search_engine_name: Literal[SearchEngineType.GOOGLE] = SearchEngineType.GOOGLE

    custom_search_config: GoogleSearchOptionalQueryParams = (
        GoogleSearchOptionalQueryParams()
    )


class GoogleSearch(SearchEngine[GoogleConfig]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.is_configured = get_google_search_settings().is_configured
        self._additional_params = self.config.custom_search_config.model_dump(
            mode="json", exclude_none=True, by_alias=True
        )

    @property
    def requires_scraping(self) -> bool:
        return True

    def _update_pagination_params(self, start_index: int, num_fetch: int):
        self._additional_params = self._additional_params | {
            "start": start_index,
            "num": num_fetch,
        }

    def _update_date_restrict_params(self, date_restrict: str | None):
        if date_restrict:
            self._additional_params = self._additional_params | {
                "dateRestrict": date_restrict,
            }

    def _get_request_params(self, query, **kwargs) -> dict:
        """Get the request parameters."""
        # Ensure required settings are available
        google_search_settings = get_google_search_settings()
        assert google_search_settings.is_configured
        assert google_search_settings.search_engine_id is not None
        assert google_search_settings.api_key is not None

        # Create query parameters using the Pydantic model
        query_params = GoogleSearchQueryParams(
            q=query,
            cx=google_search_settings.search_engine_id,
            key=google_search_settings.api_key,
        ).model_dump(exclude_none=True)

        self._update_date_restrict_params(kwargs.get("date_restrict", None))

        params = {
            "url": google_search_settings.api_endpoint,
            "params": query_params | self._additional_params,
        }

        return params

    def _extract_urls(self, response: Response) -> list[WebSearchResult]:
        """Clean the response from the search engine."""
        results = response.json()
        links = [
            WebSearchResult(
                url=item["link"],
                snippet=item["snippet"],
                title=item.get("title", item.get("htmlTitle", "")),
            )
            for item in results["items"]
        ]
        return links

    async def _paginated_url_extraction(self, query: str, **kwargs):
        """Extract the URLs from the search results."""

        search_results = []
        start_index = 1
        fetch_size = self.config.fetch_size

        for start_index in range(1, fetch_size + 1, PAGINATION_SIZE):
            effective_num_fetch = min(fetch_size - start_index + 1, PAGINATION_SIZE)
            logger.info(
                f"Fetching {effective_num_fetch} URLs from {start_index} to {start_index + effective_num_fetch - 1}"
            )
            self._update_pagination_params(
                start_index=start_index, num_fetch=effective_num_fetch
            )
            response = await self._perform_web_search_request(query=query, **kwargs)
            search_results.extend(self._extract_urls(response=response))

        return search_results

    # TODO: Find a tracking solution
    # @track(
    #     tags=["google_search"],
    # )
    async def search(self, query: str, **kwargs) -> list[WebSearchResult]:
        """Search the web for the given query."""

        try:
            search_results = await self._paginated_url_extraction(query=query, **kwargs)
            logger.info(f"Found {len(search_results)} URLs")

        except Exception as e:
            logger.exception(f"Failed to extract URLs from search response: {e}")
            search_results = []

        return search_results

    async def _perform_web_search_request(self, query: str, **kwargs) -> Response:
        """Send a request to the search engine.

        Args:
            query: The query.
            start_index: The start index.

        Returns:
            list[dict]: The search results.

        """
        request_params = self._get_request_params(query=query, **kwargs)
        async with AsyncClient() as client:
            response = await client.get(**request_params)
        return response

    def _validate_url(self, url: str) -> bool:
        """Validate URL structure and permitted domains."""
        parsed_url = urlparse(url)
        return all(
            [
                parsed_url.scheme in ["http", "https"],
                parsed_url.netloc,
            ],
        )
