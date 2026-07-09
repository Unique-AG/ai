import logging
from typing import Any, override
from urllib.parse import urlparse

from httpx import Response
from unique_search_proxy_core.param_policy.exposable_param import ExposableParam
from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_search_proxy_core.search_engines.google.schema import GoogleConfig

from unique_web_search.client_settings import get_google_search_settings
from unique_web_search.services.client.proxy_config import async_client
from unique_web_search.services.search_engine.base import SearchEngine, SearchEngineMode
from unique_web_search.services.search_engine.registry import register_search_engine
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)
from unique_web_search.services.search_engine.utils.google.schema import (
    GoogleSearchQueryParams,
)

_LOGGER = logging.getLogger(__name__)

# Pagingation size fixed to 10 because of the Google Search API limit
PAGINATION_SIZE = 10

_EXPOSABLE_LEGACY_API_KEYS: tuple[tuple[str, str], ...] = (
    ("gl", "gl"),
    ("hl", "hl"),
    ("lr", "lr"),
    ("date_restrict", "dateRestrict"),
    ("exact_terms", "exactTerms"),
    ("exclude_terms", "excludeTerms"),
    ("file_type", "fileType"),
    ("site_search", "siteSearch"),
    ("site_search_filter", "siteSearchFilter"),
    ("sort", "sort"),
)


def _exposable_value(param: ExposableParam[Any]) -> Any | None:
    if param.is_active():
        return param.value
    return None


def _google_legacy_query_params(config: GoogleConfig) -> dict[str, Any]:
    params: dict[str, Any] = {"safe": config.safe}
    for field_name, api_key in _EXPOSABLE_LEGACY_API_KEYS:
        value = _exposable_value(getattr(config, field_name))
        if value is not None:
            params[api_key] = value
    return params


@register_search_engine(
    name="google",
    key=SearchEngineType.GOOGLE,
    config_cls=GoogleConfig,
    mode=SearchEngineMode.STANDARD,
    config_display_name="Google",
)
class GoogleSearch(SearchEngine[GoogleConfig]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._additional_params = _google_legacy_query_params(self.config)

    @property
    def requires_scraping(self) -> bool:
        return True

    @override
    async def _legacy_search(
        self,
        query: str,
        params: dict[str, Any],
    ) -> list[WebSearchResult]:
        """Search the web for the given query."""
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
        params: dict[str, Any],
    ) -> Response:
        """Send a request to the search engine.

        Args:
            query: The query.
            start_index: The start index.

        Returns:
            list[dict]: The search results.

        """
        request_params = self._get_request_params(query=query, params=params)
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

    def _get_request_params(self, query: str, params: dict[str, Any]) -> dict:
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

        date_restrict = params.get("date_restrict")
        self._update_date_restrict_params(date_restrict)

        params_out = {
            "url": google_search_settings.api_endpoint,
            "params": query_params | self._additional_params,
        }

        return params_out

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

    async def _paginated_url_extraction(self, query: str, params: dict[str, Any]):
        """Extract the URLs from the search results."""

        search_results = []
        start_index = 1
        fetch_size = self.config.fetch_size

        for start_index in range(1, fetch_size + 1, PAGINATION_SIZE):
            effective_num_fetch = min(fetch_size - start_index + 1, PAGINATION_SIZE)
            _LOGGER.info(
                f"Fetching {effective_num_fetch} URLs from {start_index} to {start_index + effective_num_fetch - 1}"
            )
            self._update_pagination_params(
                start_index=start_index, num_fetch=effective_num_fetch
            )
            response = await self._perform_web_search_request(
                query=query,
                params=params,
            )
            search_results.extend(self._extract_urls(response=response))

        return search_results
