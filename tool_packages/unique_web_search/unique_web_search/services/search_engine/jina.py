import logging
from typing import Literal

import httpx
from httpx import Response, Timeout
from pydantic import BaseModel, Field
from unique_toolkit.agentic.tools.config import get_configuration_dict

from unique_web_search.client_settings import get_jina_search_settings
from unique_web_search.services.search_engine import (
    BaseSearchEngineConfig,
    SearchEngine,
    SearchEngineType,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)

logger = logging.getLogger(__name__)


class JinaSearchOptionalParams(BaseModel):
    model_config = get_configuration_dict()

    # Request body parameters
    gl: str | None = Field(
        default=None,
        description="The country to use for the search. It's a two-letter country code.",
    )
    location: str | None = Field(
        default=None,
        description="From where you want the search query to originate. It is recommended to specify location at the city level.",
    )
    hl: str | None = Field(
        default=None,
        description="The language to use for the search. It's a two-letter language code.",
    )
    num: int | None = Field(
        default=None,
        description="Sets maximum results returned. Using num may cause latency and exclude specialized result types.",
    )
    page: int | None = Field(
        default=None,
        description="The result offset. It skips the given number of results. It's used for pagination.",
    )

    # Header parameters (X-* headers)
    x_site: str | None = Field(
        default=None,
        alias="X-Site",
        description="For in-site searches limited to the given domain",
    )
    x_with_links_summary: str | None = Field(
        default=None,
        alias="X-With-Links-Summary",
        description="'all' to gather all links or 'true' to gather unique links at the end of the response",
    )
    x_with_images_summary: str | None = Field(
        default=None,
        alias="X-With-Images-Summary",
        description="'all' to gather all images or 'true' to gather unique images at the end of the response",
    )
    x_retain_images: str | None = Field(
        default=None,
        alias="X-Retain-Images",
        description="Use 'none' to remove all images from the response",
    )
    x_no_cache: bool | None = Field(
        default=None,
        alias="X-No-Cache",
        description="Set to true to bypass cache and retrieve real-time data",
    )
    x_with_generated_alt: bool | None = Field(
        default=None,
        alias="X-With-Generated-Alt",
        description="Set to true to generate captions for images without alt tags",
    )
    x_respond_with: str | None = Field(
        default=None,
        alias="X-Respond-With",
        description="Use 'no-content' to exclude page content from the response",
    )
    x_with_favicon: bool | None = Field(
        default=None,
        alias="X-With-Favicon",
        description="Set to true to include favicon of the website in the response",
    )
    x_return_format: str | None = Field(
        default=None,
        alias="X-Return-Format",
        description="'markdown', 'html', 'text', 'screenshot', or 'pageshot' for URL of full-page screenshot",
    )
    x_engine: str | None = Field(
        default=None,
        alias="X-Engine",
        description="Specifies the engine to retrieve/parse content. Use 'browser' for best quality or 'direct' for speed",
    )
    x_with_favicons: bool | None = Field(
        default=None,
        alias="X-With-Favicons",
        description="Set to true to fetch favicon of each URL in SERP and include them in response",
    )
    x_timeout: int | None = Field(
        default=None,
        alias="X-Timeout",
        description="Specifies the maximum time (in seconds) to wait for the webpage to load",
    )
    x_set_cookie: str | None = Field(
        default=None,
        alias="X-Set-Cookie",
        description="Forwards custom cookie settings when accessing the URL, useful for pages requiring authentication",
    )
    x_proxy_url: str | None = Field(
        default=None,
        alias="X-Proxy-Url",
        description="Utilizes your proxy to access URLs, helpful for pages accessible only through specific proxies",
    )
    x_locale: str | None = Field(
        default=None,
        alias="X-Locale",
        description="Controls the browser locale to render the page. Websites may serve different content based on locale",
    )


class JinaConfig(BaseSearchEngineConfig[SearchEngineType.JINA]):
    search_engine_name: Literal[SearchEngineType.JINA] = SearchEngineType.JINA

    custom_search_config: JinaSearchOptionalParams = JinaSearchOptionalParams()


class JinaSearchParams(BaseModel):
    q: str = Field(description="Search query")
    gl: str | None = Field(
        default=None,
        description="The country to use for the search. It's a two-letter country code.",
    )
    location: str | None = Field(
        default=None,
        description="From where you want the search query to originate.",
    )
    hl: str | None = Field(
        default=None,
        description="The language to use for the search. It's a two-letter language code.",
    )
    num: int | None = Field(
        default=None,
        description="Sets maximum results returned.",
    )
    page: int | None = Field(
        default=None,
        description="The result offset for pagination.",
    )


class JinaSearch(SearchEngine[JinaConfig]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.is_configured = get_jina_search_settings().is_configured

    @property
    def requires_scraping(self) -> bool:
        return False

    def _get_request_params(self, query, **kwargs) -> dict:
        """Get the request parameters for Jina Search API."""
        # Ensure required settings are available
        jina_search_settings = get_jina_search_settings()
        assert jina_search_settings.api_key is not None

        # Separate body parameters from header parameters
        config_dict = self.config.custom_search_config.model_dump(
            mode="json", exclude_none=True, by_alias=True
        )

        # Body parameters (non-header fields)
        body_params = {
            k: v
            for k, v in config_dict.items()
            if v is not None and not k.startswith("X-")
        }

        # Header parameters (X-* fields)
        header_params = {
            k: str(v).lower() if v is not None and isinstance(v, bool) else v
            for k, v in config_dict.items()
            if k.startswith("X-")
        }

        # Create search parameters for the request body
        search_params = JinaSearchParams(
            q=query,
            num=self.config.fetch_size,
            **body_params,
        )

        # Base headers
        headers = {
            "Authorization": f"Bearer {jina_search_settings.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Add optional headers
        headers.update(header_params)

        params = {
            "url": jina_search_settings.search_api_endpoint,
            "headers": headers,
            "json": search_params.model_dump(exclude_none=True),
        }

        return params

    def _extract_urls(self, response: Response) -> list[WebSearchResult]:
        """Extract URLs from Jina Search API response."""
        try:
            results = response.json()

            # Handle error responses
            if response.status_code != 200:
                logger.error(f"Jina API error: {results}")
                return []

            # Extract data from Jina API response
            data = results.get("data", [])
            if not data:
                logger.warning("No search results found in Jina API response")
                return []

            extracted_results = []
            for item in data:
                try:
                    search_result = WebSearchResult(
                        url=item["url"],
                        title=item.get("title", ""),
                        snippet=item.get("description", ""),
                        content=item.get("content", ""),
                    )
                    extracted_results.append(search_result)
                except KeyError as e:
                    logger.warning(f"Missing required field in search result: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing search result: {e}")
                    continue

            return extracted_results

        except Exception as e:
            logger.error(f"Failed to parse Jina API response: {e}")
            return []

    async def _perform_web_search_request(self, query: str, **kwargs) -> Response:
        """Send a request to the Jina Search API.

        Args:
            query: The search query.

        Returns:
            Response: The HTTP response from Jina API.
        """
        request_params = self._get_request_params(query=query, **kwargs)

        # Use POST method as required by Jina Search API
        async with httpx.AsyncClient() as client:
            response = await client.post(**request_params, timeout=Timeout(timeout=120))
        return response

    # TODO: Find a tracking solution
    # @track(
    #     tags=["jina_search"],
    # )
    async def search(self, query: str, **kwargs) -> list[WebSearchResult]:
        """Search the web for the given query using Jina Search API."""
        try:
            response = await self._perform_web_search_request(query=query, **kwargs)
            search_results = self._extract_urls(response=response)
            logger.info(f"Found {len(search_results)} URLs")

        except Exception as e:
            logger.exception(f"Failed to extract URLs from Jina search response: {e}")
            search_results = []

        return search_results
