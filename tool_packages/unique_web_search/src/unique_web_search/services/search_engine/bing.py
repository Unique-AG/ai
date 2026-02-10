import logging
from typing import Literal

from pydantic import BaseModel, Field
from unique_toolkit.agentic.tools.config import get_configuration_dict

from unique_web_search.services.search_engine.base import (
    BaseSearchEngineConfig,
    SearchEngine,
    SearchEngineType,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)
from unique_web_search.services.search_engine.utils.bing import (
    create_and_process_run,
    credentials_are_valid,
    get_credentials,
    get_project_client,
)

_LOGGER = logging.getLogger(__name__)


class BingSearchOptionalQueryParams(BaseModel):
    model_config = get_configuration_dict()

    requires_scraping: bool = Field(
        default=False,
        description="Whether the search engine requires scraping.",
    )


class BingSearchConfig(
    BaseSearchEngineConfig[SearchEngineType.BING], BingSearchOptionalQueryParams
):
    search_engine_name: Literal[SearchEngineType.BING] = SearchEngineType.BING


class BingSearch(SearchEngine[BingSearchConfig]):
    def __init__(
        self,
        config: BingSearchConfig,
    ):
        super().__init__(config)
        self.credentials = get_credentials()
        self.is_configured = credentials_are_valid(self.credentials)

    @property
    def requires_scraping(self) -> bool:
        return self.config.requires_scraping

    async def search(self, query: str, **kwargs) -> list[WebSearchResult]:
        project = get_project_client(self.credentials)

        search_results = create_and_process_run(project, query, self.config.fetch_size)

        return search_results
