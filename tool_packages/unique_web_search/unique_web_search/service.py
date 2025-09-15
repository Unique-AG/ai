from typing_extensions import override
from unique_toolkit._common.chunk_relevancy_sorter.service import ChunkRelevancySorter
from unique_toolkit.evals.schemas import EvaluationMetricName
from unique_toolkit.history_manager.utils import transform_chunks_to_string
from unique_toolkit.language_model import LanguageModelToolMessage
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)
from unique_toolkit.tools.factory import ToolFactory
from unique_toolkit.tools.schemas import ToolCallResponse
from unique_toolkit.tools.tool import AgentChunksHandler, LanguageModelMessage, Tool
from unique_toolkit.tools.tool_progress_reporter import ProgressState

from unique_web_search.config import WebSearchConfig
from unique_web_search.schema import WebSearchPlan, WebSearchToolParameters
from unique_web_search.services.content_processing import ContentProcessor, WebPageChunk
from unique_web_search.services.crawlers import get_crawler_service
from unique_web_search.services.executors import (
    WebSearchV1Executor,
    WebSearchV2Executor,
)
from unique_web_search.services.search_engine import get_search_engine_service
from unique_web_search.utils import reduce_sources_to_token_limit


class WebSearchTool(Tool[WebSearchConfig]):
    name = "WebSearch"

    def __init__(self, configuration: WebSearchConfig, *args, **kwargs):
        super().__init__(configuration, *args, **kwargs)
        self.language_model = self.config.language_model

        self.search_engine_service = get_search_engine_service(
            self.config.search_engine_config
        )
        self.crawler_service = get_crawler_service(self.config.crawler_config)
        self.chunk_relevancy_sorter = ChunkRelevancySorter(self.event)
        self.company_id = self.event.company_id
        self.chat_history_token_length = 0
        self.chat_history_chat_messages = self._chat_service.get_full_history()
        self.debug_info = {}
        self.content_processor = ContentProcessor(
            event=self.event,
            config=self.config.content_processor_config,
            language_model=self.language_model,
        )
        self.debug = self.config.debug

        def content_reducer(web_page_chunks: list[WebPageChunk]) -> list[WebPageChunk]:
            return reduce_sources_to_token_limit(
                web_page_chunks,
                self.config.language_model_max_input_tokens,
                self.config.percentage_of_input_tokens_for_sources,
                self.config.limit_token_sources,
                self.language_model,
                self.chat_history_token_length,
            )

        self.content_reducer = content_reducer

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        self.tool_parameter_calls = (
            WebSearchPlan
            if self.config.experimental_features.v2_mode.enabled
            else WebSearchToolParameters.from_tool_parameter_query_description(
                self.config.tool_parameters_config.query_description,
                self.config.tool_parameters_config.date_restrict_description,
            )
        )

        tool_description = (
            self.config.experimental_features.v2_mode.tool_description
            if self.config.experimental_features.v2_mode.enabled
            else self.config.tool_description
        )

        return LanguageModelToolDescription(
            name=self.name,
            description=tool_description,
            parameters=self.tool_parameter_calls,
        )

    def tool_description_for_system_prompt(self) -> str:
        if self.config.experimental_features.v2_mode.enabled:
            return self.config.experimental_features.v2_mode.tool_description_for_system_prompt.replace(
                "$max_steps", str(self.config.experimental_features.v2_mode.max_steps)
            )

        return self.config.tool_description_for_system_prompt

    def tool_format_information_for_system_prompt(self) -> str:
        return self.config.tool_format_information_for_system_prompt

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return self.config.evaluation_check_list

    @override
    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        self.logger.info("Running the WebSearch tool")

        parameters = self.tool_parameter_calls.model_validate(
            tool_call.arguments,
        )
        self.debug_info = {"tool_call": tool_call.model_dump()}

        executor = self._get_executor(tool_call, parameters)

        try:
            content_chunks, executor_debug_info = await executor.run()

            self.debug_info = self.debug_info | executor_debug_info

            self.debug_info["num_chunks_in_final_prompts"] = len(content_chunks)

            if self.tool_progress_reporter:
                await self.tool_progress_reporter.notify_from_tool_call(
                    tool_call=tool_call,
                    name=executor.notify_name,
                    message=executor.notify_message,
                    state=ProgressState.FINISHED,
                )

            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                debug_info=self.debug_info,
                content_chunks=content_chunks,
            )
        except Exception as e:
            self.logger.exception(f"Error executing WebSearch tool: {e}")

            if self.tool_progress_reporter:
                await self.tool_progress_reporter.notify_from_tool_call(
                    tool_call=tool_call,
                    name=executor.notify_name,
                    message=executor.notify_message,
                    state=ProgressState.FAILED,
                )

            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                debug_info=self.debug_info,
                error_message=str(e),
            )

    def _get_executor(
        self,
        tool_call: LanguageModelFunction,
        parameters: WebSearchPlan | WebSearchToolParameters,
    ) -> WebSearchV1Executor | WebSearchV2Executor:
        if isinstance(parameters, WebSearchPlan):
            return WebSearchV2Executor(
                search_service=self.search_engine_service,
                language_model_service=self.language_model_service,
                language_model=self.language_model,
                crawler_service=self.crawler_service,
                tool_call=tool_call,
                tool_parameters=parameters,
                company_id=self.company_id,
                content_processor=self.content_processor,
                chunk_relevancy_sorter=self.chunk_relevancy_sorter,
                chunk_relevancy_sort_config=self.config.chunk_relevancy_sort_config,
                tool_progress_reporter=self.tool_progress_reporter,
                content_reducer=self.content_reducer,
                max_steps=self.config.experimental_features.v2_mode.max_steps,
                debug=self.debug,
            )
        elif isinstance(parameters, WebSearchToolParameters):
            return WebSearchV1Executor(
                search_service=self.search_engine_service,
                language_model_service=self.language_model_service,
                language_model=self.language_model,
                crawler_service=self.crawler_service,
                tool_call=tool_call,
                tool_parameters=parameters,
                company_id=self.company_id,
                mode=self.config.experimental_features.v1_mode.refine_query_mode,
                max_queries=self.config.experimental_features.v1_mode.max_queries,
                content_processor=self.content_processor,
                chunk_relevancy_sorter=self.chunk_relevancy_sorter,
                chunk_relevancy_sort_config=self.config.chunk_relevancy_sort_config,
                tool_progress_reporter=self.tool_progress_reporter,
                content_reducer=self.content_reducer,
                refine_query_system_prompt=self.config.query_refinement_config.system_prompt,
                debug=self.debug,
            )
        else:
            raise ValueError(f"Invalid parameters: {parameters}")

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

    def get_evaluation_checks_based_on_tool_response(
        self,
        tool_response: ToolCallResponse,
    ) -> list[EvaluationMetricName]:
        evaluation_check_list = self.evaluation_check_list()

        # Check if the tool response is empty
        if not tool_response.content_chunks:
            return []
        return evaluation_check_list


ToolFactory.register_tool(WebSearchTool, WebSearchConfig)
