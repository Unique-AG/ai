from datetime import datetime
from time import time

from pydantic import BaseModel, ConfigDict, Field, create_model
from typing_extensions import override
from unique_toolkit._common.chunk_relevancy_sorter.service import ChunkRelevancySorter
from unique_toolkit._common.utils.structured_output.schema import StructuredOutputModel
from unique_toolkit.chat.schemas import ChatMessage
from unique_toolkit.chat.service import LanguageModelToolDescription
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.content.utils import (
    count_tokens,
)
from unique_toolkit.evals.schemas import EvaluationMetricName
from unique_toolkit.history_manager.utils import transform_chunks_to_string
from unique_toolkit.language_model.builder import MessagesBuilder
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelMessage,
    LanguageModelToolMessage,
)
from unique_toolkit.tools.agent_chunks_hanlder import AgentChunksHandler
from unique_toolkit.tools.factory import ToolFactory
from unique_toolkit.tools.schemas import ToolCallResponse
from unique_toolkit.tools.tool import Tool
from unique_toolkit.tools.tool_progress_reporter import ProgressState

from unique_web_search.config import WebSearchConfig
from unique_web_search.services.content_processing.config import WebPageChunk
from unique_web_search.services.content_processing.service import ContentProcessor
from unique_web_search.services.search_and_crawl import SearchAndCrawlService
from unique_web_search.services.search_engine.base import SearchEngineType
from unique_web_search.services.search_engine.firecrawl import FireCrawlSearch
from unique_web_search.services.search_engine.google import GoogleSearch
from unique_web_search.services.search_engine.jina import JinaSearch
from unique_web_search.services.search_engine.tavily import TavilySearch
from unique_web_search.utils import _query_params_to_human_string


class RefinedQuery(StructuredOutputModel):
    """A refined query."""

    optimized_query: str = Field(description="The refined query.")


class WebSearchToolParameters(BaseModel):
    """Parameters for the Websearch tool."""

    model_config = ConfigDict(extra="forbid")
    query: str
    date_restrict: str | None

    @classmethod
    def from_tool_parameter_query_description(
        cls, query_description: str, date_restrict_description: str
    ) -> type[BaseModel]:
        """Create a new model with the query field."""
        return create_model(
            cls.__name__,
            query=(str, Field(description=query_description)),
            date_restrict=(
                str | None,
                Field(description=date_restrict_description),
            ),
            __base__=cls,
        )


class WebSearchTool(Tool[WebSearchConfig]):
    name = "WebSearch"

    def __init__(self, configuration: WebSearchConfig, *args, **kwargs):
        super().__init__(configuration, *args, **kwargs)

        self.chunk_relevancy_sorter = ChunkRelevancySorter(self.event)

        self.language_model = self.config.language_model

        self.chat_history_chat_messages: list[ChatMessage] = []
        self.chat_history_token_length = 0
        self.chat_history_language_model_messages: list[LanguageModelMessage] = []
        self.chat_history_list_string: list[str] = []
        self.chat_history_string: str = ""

        self.index = 1000

        self.search_and_crawl_service = SearchAndCrawlService(
            company_id=self.event.company_id,
            search_engine_config=self.config.search_engine_config,
            crawler_config=self.config.crawler_config,
        )

        self.content_processor = ContentProcessor(
            event=self.event,
            config=self.config.content_processor_config,
            language_model=self.config.language_model,
        )

    def _get_search_engine_service(self):
        """Get the search engine service based on the search engine type."""
        search_engine_name = self.config.search_engine_config.search_engine_name

        match search_engine_name:
            case SearchEngineType.JINA:
                return JinaSearch(self.event, self.config.search_engine_config)
            case SearchEngineType.GOOGLE:
                return GoogleSearch(self.event, self.config.search_engine_config)
            case SearchEngineType.FIRECRAWL:
                return FireCrawlSearch(self.event, self.config.search_engine_config)
            case SearchEngineType.TAVILY:
                return TavilySearch(self.event, self.config.search_engine_config)

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name=self.name,
            description=self.config.tool_description,
            parameters=WebSearchToolParameters.from_tool_parameter_query_description(
                self.config.tool_parameters_config.query_description,
                self.config.tool_parameters_config.date_restrict_description,
            ),
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

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        """Run search and generate answer to the user query"""
        self.logger.info("Running the WebSearch tool")

        debug_info = {}

        self.event.payload.user_message.text = (
            self.event.payload.user_message.text or ""
        )

        ###
        # 1. Translate the user query to the search engine query
        ###
        start_time_step_1 = time()
        parameters = WebSearchToolParameters.model_validate(
            tool_call.arguments,
        )

        search_query = parameters.query
        date_restrict = parameters.date_restrict
        debug_info["search_query"] = search_query
        debug_info["date_restrict"] = date_restrict

        # Refine the query to be more specific and relevant to the user's question.
        try:
            if self.config.query_refinement_config.enabled:
                refined_query = await self._refine_query(search_query)
                debug_info["refined_query"] = refined_query.optimized_query
                search_query = refined_query.optimized_query
        except Exception:
            self.logger.exception(
                "An expected error occurred while refining the query. Query refinement is skipped."
            )

        query_human_string = _query_params_to_human_string(search_query, date_restrict)

        if self.tool_progress_reporter:
            await self.tool_progress_reporter.notify_from_tool_call(
                tool_call=tool_call,
                name="**Web search**",
                message=f"{query_human_string}",
                state=ProgressState.RUNNING,
            )

        self.logger.debug(f"Debug info: {debug_info}")

        # debug_info["question_language"] = language
        end_time_step_1 = time()
        self.logger.info(
            f"Step 1: Translate the user query to the search engine query took {end_time_step_1 - start_time_step_1} seconds",
        )

        ###
        # 2. Search the web for relevant information
        ###
        start_time_step_2 = time()
        try:
            (
                search_results,
                time_info,
            ) = await self.search_and_crawl_service.search_and_crawl(
                query=search_query,
                date_restrict=date_restrict,
            )
            debug_info["search_results"] = [
                elem.model_dump() for elem in search_results
            ]
            debug_info["time_info"] = time_info
        except Exception as e:
            self.logger.error(f"An error occurred while searching the web: {e}")
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                content_chunks=[],
                error_message=str(e),
                debug_info=debug_info,
            )

        end_time_step_2 = time()
        self.logger.info(
            f"Step 2: Search the web for relevant information took {end_time_step_2 - start_time_step_2} seconds",
        )

        try:
            web_page_chunks = await self.content_processor.run(
                query=search_query,
                pages=search_results,
            )
        except Exception as e:
            self.logger.error(
                f"An error occurred while analyzing relevant web pages: {e}"
            )
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                content_chunks=[],
                error_message=str(e),
                debug_info=debug_info,
            )

        ###
        # 3. Select relevant sources
        ###
        start_time_step_3 = time()
        if self.tool_progress_reporter:
            await self.tool_progress_reporter.notify_from_tool_call(
                tool_call=tool_call,
                name="**Web search**",
                message=f"{query_human_string} (_Postprocessing search results_)",
                state=ProgressState.RUNNING,
            )
        if not web_page_chunks:
            self.logger.info("No relevant sources found")
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                content_chunks=[],
                debug_info=debug_info,
            )
        relevant_sources = await self._select_relevant_sources(
            search_query,
            web_page_chunks,
            tool_call,
        )
        debug_info["num chunks in final prompts"] = len(relevant_sources)

        end_time_step_3 = time()
        self.logger.info(
            f"Step 3: Select relevant sources took {end_time_step_3 - start_time_step_3} seconds",
        )

        if self.tool_progress_reporter:
            await self.tool_progress_reporter.notify_from_tool_call(
                tool_call=tool_call,
                name="**Web search**",
                message=f"{query_human_string}",
                state=ProgressState.FINISHED,
            )

        return ToolCallResponse(
            id=tool_call.id,  # type: ignore
            name=self.name,
            content_chunks=relevant_sources,
            debug_info=debug_info,
        )

    async def _select_relevant_sources(
        self,
        search_query: str,
        web_page_chunks: list[WebPageChunk],
        tool_call: LanguageModelFunction,
    ) -> list[ContentChunk]:
        # Reduce the sources to the token limit defined in the config
        top_results = self._reduce_sources_to_token_limit(web_page_chunks)

        # Convert WebPageChunks to ContentChunk format
        content = [chunk.to_content_chunk() for chunk in top_results]

        # Apply chunk relevancy sorting
        if self.config.chunk_relevancy_sort_config.enabled:
            if self.tool_progress_reporter:
                await self.tool_progress_reporter.notify_from_tool_call(
                    tool_call=tool_call,
                    name="**Web search**",
                    message=f"{search_query} (_Resorting {len(content)} search results_ 🔄)",
                    state=ProgressState.RUNNING,
                )
            sorted_chunks = await self.chunk_relevancy_sorter.run(
                input_text=search_query,
                chunks=content,
                config=self.config.chunk_relevancy_sort_config,
            )
            self.logger.info(f"Sorting chunks message: {sorted_chunks.user_message}")
            return sorted_chunks.content_chunks
        else:
            return content

    def _get_max_tokens(self) -> int:
        if self.config.language_model_max_input_tokens is not None:
            max_tokens = int(
                self.config.language_model_max_input_tokens
                * self.config.percentage_of_input_tokens_for_sources
            )
            self.logger.debug(
                "Using %s of max tokens %s as token limit: %s",
                self.config.percentage_of_input_tokens_for_sources,
                self.config.language_model_max_input_tokens,
                max_tokens,
            )
            return max_tokens
        else:
            self.logger.debug(
                "language model input context size is not set, using default max tokens"
            )
            return (
                min(
                    self.config.limit_token_sources,
                    self.language_model.token_limits.token_limit_input - 1000,
                )
                if self.language_model.token_limits
                and self.language_model.token_limits.token_limit_input
                else self.config.limit_token_sources
            )

    def _reduce_sources_to_token_limit(
        self, web_page_chunks: list[WebPageChunk]
    ) -> list[WebPageChunk]:
        total_tokens = 0
        selected_chunks = []

        max_token_sources = self._get_max_tokens()

        for chunk in web_page_chunks:
            if total_tokens < max_token_sources - self.chat_history_token_length:
                total_tokens += count_tokens(text=chunk.content)
                selected_chunks.append(chunk)
            else:
                break

        return selected_chunks

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
        self.logger.debug(
            f"Appending tool call result to history: {tool_response.name}"
        )
        # Initialize content_chunks if None
        content_chunks = tool_response.content_chunks or []

        # Get the maximum source number in the loop history
        max_source_number = len(agent_chunks_handler.chunks)

        # Transform content chunks into sources to be appended to tool result
        sources = transform_chunks_to_string(
            content_chunks,
            max_source_number,
            None,  # Use None for SourceFormatConfig
            self.config.experimental_features.full_sources_serialize_dump,
        )

        # Append the result to the history
        return LanguageModelToolMessage(
            content=sources,
            tool_call_id=tool_response.id,  # type: ignore
            name=tool_response.name,
        )

    # TODO: How to do tracking nicely
    # @track(
    #     tags=["web_search_tool", "refine_query"],
    # )
    async def _refine_query(self, query: str) -> RefinedQuery:
        """Refine the query to be more specific and relevant to the user's question."""
        messages = (
            MessagesBuilder()
            .system_message_append(self.config.query_refinement_config.system_prompt)
            .user_message_append(
                f"Current date: {datetime.now().strftime('%Y-%m-%d')}"
                f"Refine the following query: {query}"
            )
            .build()
        )
        response = await self.language_model_service.complete_async(
            messages,
            model_name=self.language_model.name,
            structured_output_model=RefinedQuery,
            structured_output_enforce_schema=True,
        )

        parsed_response = response.choices[0].message.parsed
        if parsed_response is None:
            raise ValueError("Failed to parse insights from LLM response")

        return RefinedQuery.model_validate(parsed_response)


ToolFactory.register_tool(WebSearchTool, WebSearchConfig)
