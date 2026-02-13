import asyncio
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from unique_toolkit._common.default_language_model import DEFAULT_GPT_4o
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.agentic.tools.config import get_configuration_dict

from unique_web_search.services.search_engine.base import (
    BaseSearchEngineConfig,
    SearchEngine,
    SearchEngineType,
    get_search_engine_model_config,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)
from unique_web_search.services.search_engine.utils.bing import (
    ResponseParser,
    create_and_process_run,
    credentials_are_valid,
    get_credentials,
    get_project_client,
)
from unique_web_search.services.search_engine.utils.bing.models import (
    GENERATION_INSTRUCTIONS,
)


class BingSearchOptionalQueryParams(BaseModel):
    model_config = get_configuration_dict()

    requires_scraping: bool = Field(
        default=False,
        description="Whether the search engine requires scraping.",
    )


class BingSearchConfig(
    BaseSearchEngineConfig[SearchEngineType.BING], BingSearchOptionalQueryParams
):
    model_config = get_search_engine_model_config(SearchEngineType.BING)

    search_engine_name: Literal[SearchEngineType.BING] = SearchEngineType.BING

    agent_id: str = Field(
        default="",
        description="The ID of the agent to use for the search.",
    )
    endpoint: str = Field(
        default="",
        description="The endpoint to use for the search.",
    )

    generation_instructions: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(GENERATION_INSTRUCTIONS.split("\n"))
        ),
    ] = Field(
        default=GENERATION_INSTRUCTIONS,
        description="The generation instructions to be used in Microsoft Foundry Agents.",
    )

    language_model: LMI = get_LMI_default_field(
        DEFAULT_GPT_4o,
        description="The language model to use in as a fallback parser if the agent response is not a valid JSON.",
    )


class BingSearch(SearchEngine[BingSearchConfig]):
    def __init__(
        self,
        config: BingSearchConfig,
        response_parsers: list[ResponseParser],
    ):
        super().__init__(config)
        self.credentials = get_credentials()
        self.response_parsers = response_parsers

    @property
    def is_configured(self) -> bool:
        async def _is_configured() -> bool:
            return await credentials_are_valid(self.credentials)

        return asyncio.run(_is_configured())

    @property
    def requires_scraping(self) -> bool:
        return self.config.requires_scraping

    async def search(self, query: str, **kwargs) -> list[WebSearchResult]:
        agent_client = get_project_client(self.credentials, self.config.endpoint)

        search_results = await create_and_process_run(
            agent_client,
            agent_id=self.config.agent_id,
            query=query,
            fetch_size=self.config.fetch_size,
            response_parsers_strategies=self.response_parsers,
            generation_instructions=self.config.generation_instructions,
        )

        return search_results
