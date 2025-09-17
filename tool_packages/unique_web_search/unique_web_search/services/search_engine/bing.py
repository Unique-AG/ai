import json
import logging
from typing import Literal

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MessageTextContent
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel, Field
from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI
from unique_toolkit.language_model.builder import MessagesBuilder
from unique_toolkit.tools.config import get_configuration_dict

from unique_web_search.services.search_engine.base import (
    BaseSearchEngineConfig,
    SearchEngine,
    SearchEngineType,
)
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)

logger = logging.getLogger(__name__)


class BingSearchOptionalQueryParams(BaseModel):
    model_config = get_configuration_dict()

    agent_id: str = Field(
        default="",
        description="The ID of the agent to use for the search.",
    )
    conn_str: str = Field(
        default="",
        description="The connection string to use for the search.",
    )
    requires_scraping: bool = Field(
        default=False,
        description="Whether the search engine requires scraping.",
    )


class BingSearchConfig(BaseSearchEngineConfig[SearchEngineType.BING]):
    search_engine_name: Literal[SearchEngineType.BING] = SearchEngineType.BING

    custom_search_config: BingSearchOptionalQueryParams = (
        BingSearchOptionalQueryParams()
    )


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
        self.credentials = self._authenticate()
        self.is_configured = self.credentials._successful_credential is not None

    @property
    def requires_scraping(self) -> bool:
        return self.config.custom_search_config.requires_scraping

    def _authenticate(self):
        credentials = DefaultAzureCredential()
        return credentials

    async def search(self, query: str, **kwargs) -> list[WebSearchResult]:
        project_client = AIProjectClient.from_connection_string(
            credential=self.credentials,
            conn_str=self.config.custom_search_config.conn_str,
        )

        agent = project_client.agents.get_agent(
            self.config.custom_search_config.agent_id
        )

        thread = project_client.agents.create_thread()

        project_client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content=query,
        )

        project_client.agents.create_and_process_run(
            thread_id=thread.id, agent_id=agent.id
        )

        messages = project_client.agents.list_messages(thread_id=thread.id)
        messages = messages.text_messages

        return await self._structured_output(messages)

    async def _structured_output(
        self, messages: list[MessageTextContent]
    ) -> list[WebSearchResult]:
        messages_dict = json.dumps(
            [message.as_dict() for message in messages], indent=4
        )
        llm_messages = (
            MessagesBuilder()
            .system_message_append(
                "You are a helpful assistant that can structure results from a referenced response to web page content."
            )
            .user_message_append(messages_dict)
            .build()
        )

        class WebSearchResults(BaseModel):
            results: list[WebSearchResult]

        response = await self.language_model_service.complete_async(
            llm_messages,
            model_name=self.lmi.name,
            structured_output_model=WebSearchResults,
        )

        response = WebSearchResults.model_validate(response.choices[0].message.parsed)
        return response.results
