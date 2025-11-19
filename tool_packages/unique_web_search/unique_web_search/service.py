from time import time

from typing_extensions import override
from unique_toolkit._common.chunk_relevancy_sorter.service import ChunkRelevancySorter
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import (
    Tool,
)
from unique_toolkit.agentic.tools.tool_progress_reporter import ProgressState
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)

from unique_web_search.config import WebSearchConfig
from unique_web_search.schema import WebSearchPlan, WebSearchToolParameters
from unique_web_search.services.content_processing import ContentProcessor, WebPageChunk
from unique_web_search.services.crawlers import get_crawler_service
from unique_web_search.services.executors import (
    WebSearchV1Executor,
    WebSearchV2Executor,
)
from unique_web_search.services.executors.configs import WebSearchMode
from unique_web_search.services.search_engine import get_search_engine_service
from unique_web_search.utils import WebSearchDebugInfo, reduce_sources_to_token_limit


class WebSearchTool(Tool[WebSearchConfig]):
    name = "WebSearch"

    def __init__(self, configuration: WebSearchConfig, *args, **kwargs):
        super().__init__(configuration, *args, **kwargs)
        self.language_model = self.config.language_model

        self.search_engine_service = get_search_engine_service(
            self.config.search_engine_config,
            self.language_model_service,
            self.language_model,
        )
        self.crawler_service = get_crawler_service(self.config.crawler_config)
        self.chunk_relevancy_sorter = ChunkRelevancySorter(self.event)
        self.company_id = self.event.company_id
        self.chat_history_token_length = 0
        self.chat_history_chat_messages = self._chat_service.get_full_history()
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
        if self.config.web_search_mode_config.mode == WebSearchMode.V1:
            self.tool_parameter_calls = WebSearchToolParameters.from_tool_parameter_query_description(
                self.config.web_search_mode_config.tool_parameters_description.query_description,
                self.config.web_search_mode_config.tool_parameters_description.date_restrict_description,
            )
        else:
            self.tool_parameter_calls = WebSearchPlan

        tool_description = self.config.web_search_mode_config.tool_description

        return LanguageModelToolDescription(
            name=self.name,
            description=tool_description,
            parameters=self.tool_parameter_calls,
        )

    def tool_description_for_system_prompt(self) -> str:
        if self.config.web_search_mode_config.mode == WebSearchMode.V2:
            return self.config.web_search_mode_config.tool_description_for_system_prompt.replace(
                "$max_steps", str(self.config.web_search_mode_config.max_steps)
            )
        return self.config.web_search_mode_config.tool_description_for_system_prompt

    def tool_format_information_for_system_prompt(self) -> str:
        return self.config.tool_format_information_for_system_prompt

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return self.config.evaluation_check_list

    @override
    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        self.logger.info("Running the WebSearch tool")
        start_time = time()
        parameters = self.tool_parameter_calls.model_validate(
            tool_call.arguments,
        )

        debug_info = WebSearchDebugInfo(parameters=parameters.model_dump())
        executor = self._get_executor(tool_call, parameters, debug_info)

        try:
            content_chunks = await executor.run()
            debug_info.num_chunks_in_final_prompts = len(content_chunks)
            debug_info.execution_time = time() - start_time

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
                debug_info=debug_info.model_dump(with_debug_details=self.debug),
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
                debug_info=debug_info.model_dump(with_debug_details=self.debug),
                error_message=str(e),
            )

    def _get_executor(
        self,
        tool_call: LanguageModelFunction,
        parameters: WebSearchPlan | WebSearchToolParameters,
        debug_info: WebSearchDebugInfo,
    ) -> WebSearchV1Executor | WebSearchV2Executor:
        if isinstance(parameters, WebSearchPlan):
            assert self.config.web_search_mode_config.mode == WebSearchMode.V2
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
                max_steps=self.config.web_search_mode_config.max_steps,
                debug_info=debug_info,
            )
        elif isinstance(parameters, WebSearchToolParameters):
            assert self.config.web_search_mode_config.mode == WebSearchMode.V1
            return WebSearchV1Executor(
                search_service=self.search_engine_service,
                language_model_service=self.language_model_service,
                language_model=self.language_model,
                crawler_service=self.crawler_service,
                tool_call=tool_call,
                tool_parameters=parameters,
                company_id=self.company_id,
                mode=self.config.web_search_mode_config.refine_query_mode.mode,
                max_queries=self.config.web_search_mode_config.max_queries,
                content_processor=self.content_processor,
                chunk_relevancy_sorter=self.chunk_relevancy_sorter,
                chunk_relevancy_sort_config=self.config.chunk_relevancy_sort_config,
                tool_progress_reporter=self.tool_progress_reporter,
                content_reducer=self.content_reducer,
                refine_query_system_prompt=self.config.web_search_mode_config.refine_query_mode.system_prompt,
                debug_info=debug_info,
            )
        else:
            raise ValueError(f"Invalid parameters: {parameters}")

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
