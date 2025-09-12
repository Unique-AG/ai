import json
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import override
from unique_toolkit.chat.service import LanguageModelToolDescription
from unique_toolkit.evals.schemas import EvaluationMetricName
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelMessage,
    LanguageModelToolMessage,
)
from unique_toolkit.tools.agent_chunks_hanlder import AgentChunksHandler
from unique_toolkit.tools.factory import ToolFactory
from unique_toolkit.tools.schemas import ToolCallResponse
from unique_toolkit.tools.tool import Tool

from unique_web_search.config import WebSearchConfig
from unique_web_search.search import advanced_search
from unique_web_search.services.agents.plan_agent import PlanningMode
from unique_web_search.services.content_adapter import ContentAdapter
from unique_web_search.services.crawlers import get_crawler_service
from unique_web_search.services.search_engine import get_search_engine_service


class Objective(StrEnum):
    WEB_SEARCH = "webSearch"
    WEB_READ_URL = "fetchUrl"


class WebToolParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: Objective
    query: str = Field(description="User query to find relevant information")
    urls_to_fetch: list[str] = Field(
        description="List of URLs to fetch. Should be empty list if user is not interested in fetching URLs"
    )


class WebSearchTool(Tool[WebSearchConfig]):
    name = "WebSearch"

    def __init__(self, configuration: WebSearchConfig, *args, **kwargs):
        super().__init__(configuration, *args, **kwargs)
        self.language_model = self.config.language_model

        self.search_engine_service = get_search_engine_service(
            self.config.search_engine_config
        )
        self.crawler_service = get_crawler_service(self.config.crawler_config)

        self.content_adapter = ContentAdapter(
            event=self.event,
            config=self.config.content_adapter_config,
            llm_service=self._language_model_service,
            language_model=self.config.language_model,
        )
        self.chat_history_chat_messages = self._chat_service.get_full_history()

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        parameters = WebToolParameters.model_validate(
            tool_call.arguments,
        )
        if parameters.objective == Objective.WEB_SEARCH:
            return await advanced_search(
                query=parameters.query,
                language_model_service=self._language_model_service,
                language_model=self.config.language_model.name,  # type: ignore
                mode=PlanningMode.COMPREHENSIVE,
                context=json.dumps(self.chat_history_chat_messages),
                search_service=self.search_engine_service,
                crawler_service=self.crawler_service,
                tool_call=tool_call,
                tool_progress_reporter=self.tool_progress_reporter,
                encoder_name=self.config.language_model.name,
                percentage_of_input_tokens_for_sources=self.config.percentage_of_input_tokens_for_sources,
                token_limit_input=self.config.language_model.token_limits.token_limit_input,
            )

        elif parameters.objective == Objective.WEB_READ_URL:
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=tool_call.name,
                content="Not implemented yet",
            )
        else:
            raise ValueError(f"Invalid objective: {parameters.objective}")

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name=self.name,
            description=self.name,
            parameters=WebToolParameters,
        )

    def tool_description_for_system_prompt(self) -> str:
        return self.config.tool_description_for_system_prompt

    def tool_format_information_for_system_prompt(self) -> str:
        return self.config.tool_format_information_for_system_prompt

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return self.config.evaluation_check_list

    def get_evaluation_checks_based_on_tool_response(
        self,
        tool_response: ToolCallResponse,
    ) -> list[EvaluationMetricName]:
        evaluation_check_list = self.evaluation_check_list()

        # Check if the tool response is empty
        if not tool_response.content_chunks:
            return []
        return evaluation_check_list

    def get_tool_call_result_for_loop_history(
        self,
        tool_response: ToolCallResponse,
        agent_chunks_handler: AgentChunksHandler,
    ) -> LanguageModelMessage:
        """Process the results of the tool.

        Args:
        ----
            tool_response: The tool response.
            loop_history: The loop history.

        Returns:
        -------
            The tool result to append to the loop history.

        """
        # Append the result to the history
        return LanguageModelToolMessage(
            content=tool_response.content,
            tool_call_id=tool_response.id,  # type: ignore
            name=tool_response.name,
        )

ToolFactory.register_tool(WebSearchTool, WebSearchConfig)