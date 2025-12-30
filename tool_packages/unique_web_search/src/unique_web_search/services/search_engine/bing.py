import logging
from typing import Literal

from azure.ai.agents.models import ListSortOrder
from pydantic import BaseModel, Field
from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.language_model.builder import MessagesBuilder

from unique_web_search.services.search_engine.base import (
    BaseSearchEngineConfig,
    SearchEngine,
    SearchEngineType,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
    WebSearchResults,
)
from unique_web_search.services.search_engine.utils.bing import (
    credentials_are_valid,
    get_crendentials,
    get_project_client,
)

_LOGGER = logging.getLogger(__name__)


class BingSearchOptionalQueryParams(BaseModel):
    model_config = get_configuration_dict()

    agent_id: str = Field(
        default="",
        description="The ID of the agent to use for the search.",
    )
    endpoint: str = Field(
        default="",
        description="The endpoint to use for the search.",
    )
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
        language_model_service: LanguageModelService,
        lmi: LMI,
    ):
        super().__init__(config)
        self.language_model_service = language_model_service
        self.lmi = lmi
        self.credentials = get_crendentials()
        self.is_configured = credentials_are_valid(self.credentials)

    @property
    def requires_scraping(self) -> bool:
        return self.config.requires_scraping

    async def search(self, query: str, **kwargs) -> list[WebSearchResult]:
        project = get_project_client(self.credentials, self.config.endpoint)
        agent = project.agents.get_agent(self.config.agent_id)

        thread = project.agents.threads.create()

        message = project.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=query,
        )

        run = project.agents.runs.create_and_process(
            thread_id=thread.id, agent_id=agent.id
        )

        if run.status == "failed":
            raise Exception(f"Run failed: {run.last_error}")

        messages = project.agents.messages.list(
            thread_id=thread.id, order=ListSortOrder.ASCENDING
        )

        messages_list = []
        for message in messages:
            if message.text_messages:
                messages_list.append(
                    f"{message.role}: {message.text_messages[-1].text.value}"
                )

        return await self._structured_output(messages_list)

    async def _structured_output(
        self, messages_list: list[str]
    ) -> list[WebSearchResult]:
        llm_messages = (
            MessagesBuilder()
            .system_message_append(
                "You are a helpful assistant that can structure results from a referenced response to web page content."
            )
            .user_message_append("\n".join(messages_list))
            .build()
        )
        response = await self.language_model_service.complete_async(
            llm_messages,
            model_name=self.lmi.name,
            structured_output_model=WebSearchResults,
        )

        response = WebSearchResults.model_validate(response.choices[0].message.parsed)
        return response.results
