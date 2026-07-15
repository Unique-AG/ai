import logging
from typing import override
from urllib.parse import urlparse

from httpx import Response
from pydantic import BaseModel
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_search_proxy_core.search_engines.google.schema import GoogleConfig

from unique_web_search.client_settings import get_google_search_settings
from unique_web_search.services.client.proxy_config import async_client
from unique_web_search.services.search_engine.base import SearchEngine, SearchEngineMode
from unique_web_search.services.search_engine.registry import register_search_engine
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)

_LOGGER = logging.getLogger(__name__)

# Pagination size fixed to 10 because of the Google Search API limit
PAGINATION_SIZE = 10


@register_search_engine(
    name="google",
    key=SearchEngineType.GOOGLE,
    config_cls=GoogleConfig,
    mode=SearchEngineMode.STANDARD,
    config_display_name="Google",
)
class GoogleSearch(SearchEngine[GoogleConfig]):
    @property
    def requires_scraping(self) -> bool:
        return True

    @override
    async def _legacy_search(
        self,
        query: str,
        params: ExposedParams | None,
        *,
        invocation_stats=None,
    ) -> list[WebSearchResult]:
        """Search the web for the given query."""
        del invocation_stats
        try:
            search_results = await self._paginated_url_extraction(
                query=query,
                params=params,
            )
            _LOGGER.info(f"Found {len(search_results)} URLs")

        except Exception as e:
            _LOGGER.exception(f"Failed to extract URLs from search response: {e}")
            search_results = []

        return search_results

    async def _perform_web_search_request(
        self,
        query: str,
        params: ExposedParams | None,
        *,
        start_index: int,
        num_fetch: int,
    ) -> Response:
        """Send a request to the search engine."""
        request_params = self._get_request_params(
            query=query,
            params=params,
            start_index=start_index,
            num_fetch=num_fetch,
        )
        async with async_client() as client:
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

    def _merged_request(self, query: str, params: ExposedParams | None) -> BaseModel:
        """Deployment defaults + call-time overrides -> validated Google request."""
        overrides = (
            params.model_dump(by_alias=True, exclude_none=True) if params else {}
        )
        return self.config.merge(overrides, query=query)

    def _get_request_params(
        self,
        query: str,
        params: ExposedParams | None,
        *,
        start_index: int,
        num_fetch: int,
    ) -> dict:
        """Get the request parameters."""
        google_search_settings = get_google_search_settings()
        assert google_search_settings.is_configured
        assert google_search_settings.search_engine_id is not None
        assert google_search_settings.api_key is not None
        assert google_search_settings.api_endpoint is not None

        request = self._merged_request(query, params)
        return {
            "url": google_search_settings.api_endpoint,
            "params": {
                "q": query,
                "cx": google_search_settings.search_engine_id,
                "key": google_search_settings.api_key,
                "start": start_index,
                "num": num_fetch,
                **GoogleConfig.provider_query_params(request),
            },
        }

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

    async def _paginated_url_extraction(
        self,
        query: str,
        params: ExposedParams | None,
    ):
        """Extract the URLs from the search results."""

        search_results = []
        fetch_size = self.config.fetch_size

        for start_index in range(1, fetch_size + 1, PAGINATION_SIZE):
            effective_num_fetch = min(fetch_size - start_index + 1, PAGINATION_SIZE)
            _LOGGER.info(
                f"Fetching {effective_num_fetch} URLs from {start_index} to {start_index + effective_num_fetch - 1}"
            )
            response = await self._perform_web_search_request(
                query=query,
                params=params,
                start_index=start_index,
                num_fetch=effective_num_fetch,
            )
            search_results.extend(self._extract_urls(response=response))

        return search_results
