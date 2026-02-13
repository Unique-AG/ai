import logging
from typing import Literal

from firecrawl import AsyncFirecrawl
from firecrawl.v2.types import Document, ScrapeOptions
from pydantic import BaseModel, Field

from unique_web_search.services.search_engine import (
    BaseSearchEngineConfig,
    SearchEngine,
    SearchEngineType,
)
from unique_web_search.services.search_engine.base import get_search_engine_model_config
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)
from unique_web_search.settings import env_settings

_LOGGER = logging.getLogger(__name__)


class FirecrawlSearchSettings(BaseModel):
    api_key: str | None = None

    @property
    def is_configured(self) -> bool:
        return self.api_key is not None

    @classmethod
    def from_env_settings(cls):
        missing_settings = []

        if env_settings.firecrawl_api_key is None:
            missing_settings.append("API Key")

        if missing_settings:
            _LOGGER.warning(
                f"Firecrawl Search API missing required settings: {', '.join(missing_settings)}"
            )
        else:
            _LOGGER.info("Firecrawl Search API is properly configured")

        return cls(
            api_key=env_settings.firecrawl_api_key,
        )


AllowedSource = Literal["web", "news"]


class FireCrawlConfig(BaseSearchEngineConfig[SearchEngineType.FIRECRAWL]):
    model_config = get_search_engine_model_config(SearchEngineType.FIRECRAWL)
    search_engine_name: Literal[SearchEngineType.FIRECRAWL] = SearchEngineType.FIRECRAWL

    sources: list[AllowedSource] = Field(
        default=["web", "news"],
        description="The sources to search. Only 'web' and 'news' are allowed.",
    )


_firecrawl_search_settings: FirecrawlSearchSettings | None = None


def get_firecrawl_search_settings() -> FirecrawlSearchSettings:
    global _firecrawl_search_settings
    if _firecrawl_search_settings is None:
        _firecrawl_search_settings = FirecrawlSearchSettings.from_env_settings()
    return _firecrawl_search_settings


class FireCrawlSearch(SearchEngine[FireCrawlConfig]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.is_configured = get_firecrawl_search_settings().is_configured

    @property
    def requires_scraping(self) -> bool:
        return False

    async def search(self, query: str, **kwargs) -> list[WebSearchResult]:
        """Search the web for the given query using Firecrawl.

        Args:
            query: The query.

        Returns:
            list[WebSearchResult]: The search results.
        """
        firecrawl_api_key = get_firecrawl_search_settings().api_key
        assert firecrawl_api_key is not None, "Firecrawl API key is not configured"

        fire_crawl_client = AsyncFirecrawl(api_key=firecrawl_api_key)

        response = await fire_crawl_client.search(
            query=query,
            limit=self.config.fetch_size,
            sources=self.config.sources,
            scrape_options=ScrapeOptions(formats=["markdown"]),
        )

        search_results = []
        if not response.web:
            _LOGGER.info("No web results found for the searched query.")
        else:
            for result in response.web:
                if isinstance(result, Document):
                    web_search_result = self._convert_document_to_web_search_result(
                        result
                    )
                    if web_search_result:
                        search_results.append(web_search_result)

        if not response.news:
            _LOGGER.info("No news results found for the searched query.")
        else:
            for result in response.news:
                if isinstance(result, Document):
                    web_search_result = self._convert_document_to_web_search_result(
                        result
                    )
                    if web_search_result:
                        search_results.append(web_search_result)

        return search_results

    def _convert_document_to_web_search_result(
        self, document: Document
    ) -> WebSearchResult | None:
        try:
            assert document.metadata is not None
            assert document.metadata.url is not None
            assert document.metadata.title is not None
            assert document.metadata.description is not None
            assert document.markdown is not None
            return WebSearchResult(
                url=document.metadata.url,
                title=document.metadata.title,
                snippet=document.metadata.description,
                content=document.markdown,
            )
        except Exception as e:
            _LOGGER.error(f"Unexpected missing attributes in document: {e}")
            return None
