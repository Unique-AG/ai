import logging
from datetime import datetime
from time import time

from typing_extensions import override
from unique_search_proxy_core.context import RequestContext
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_search_proxy_core.search_engines.base import BaseSearchEngineConfig
from unique_toolkit._common.chunk_relevancy_sorter.service import ChunkRelevancySorter
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.feature_flags.feature_flags import (
    feature_flags,
)
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import (
    Tool,
)
from unique_toolkit.agentic.tools.tool_progress_reporter import ProgressState
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)
from unique_toolkit.monitoring import metric_scope

from unique_web_search.config import WebSearchConfig
from unique_web_search.metrics import tool_duration, tool_empty_results, tool_errors
from unique_web_search.schema import WebSearchDebugInfo
from unique_web_search.services.argument_screening import (
    ArgumentScreeningService,
)
from unique_web_search.services.content_processing import ContentProcessor
from unique_web_search.services.crawlers import get_crawler_service
from unique_web_search.services.executors.context import (
    ExecutorCallbacks,
    ExecutorConfiguration,
    ExecutorServiceContext,
)
from unique_web_search.services.executors.modes import (
    WebSearchExecutor,
    WebSearchToolContext,
    WebSearchToolParametersInstance,
    get_mode_strategy,
)
from unique_web_search.services.message_log import WebSearchMessageLogger
from unique_web_search.services.query_elicitation import QueryElicitationService
from unique_web_search.services.search_engine import (
    get_search_engine_service,
)
from unique_web_search.utils import (
    WebPageChunk,
    reduce_sources_to_token_limit,
)

_LOGGER = logging.getLogger(__name__)


class WebSearchTool(Tool[WebSearchConfig]):
    name = "WebSearch"

    def __init__(
        self,
        configuration: WebSearchConfig,
        *args,
        language_model_orchestrator: LanguageModelInfo | None = None,
        **kwargs,
    ):
        super().__init__(configuration, *args, **kwargs)
        # TODO (UN-17100): Propagate orchestrator LLM into tool initialization.
        # Until then, fall back to the per-tool token-counting model.
        self.language_model_orchestrator = (
            language_model_orchestrator or configuration.token_counting_language_model
        )

        self.chunk_relevancy_sorter = ChunkRelevancySorter(self.event)
        self.company_id = self.event.company_id
        self.request_context = RequestContext(
            company_id=self.event.company_id,
            user_id=self.event.user_id,
            chat_id=self.event.payload.chat_id,
        )
        self.search_engine_service = get_search_engine_service(
            self.config.search_engine_config,
            self.language_model_service,
            request_context=self.request_context,
        )
        self.crawler_service = get_crawler_service(
            self.config.crawler_config,
            request_context=self.request_context,
        )
        self.chat_history_token_length = 0
        self.chat_history_chat_messages = self._chat_service.get_full_history()

        self.content_processor = ContentProcessor(
            language_model_service=self.language_model_service,
            config=self.config.content_processor_config,
            encoder=self.language_model_orchestrator.get_encoder(),
            decoder=self.language_model_orchestrator.get_decoder(),
        )
        self.debug = self.config.debug
        self._display_name = kwargs.get("display_name", "Web Search")
        self.exposed_params_cls = self._resolve_exposed_params_cls()
        self._mode_strategy = get_mode_strategy(self.config.web_search_mode_config)

        def content_reducer(web_page_chunks: list[WebPageChunk]) -> list[WebPageChunk]:
            return reduce_sources_to_token_limit(
                web_page_chunks,
                self.config.language_model_max_input_tokens,
                self.config.percentage_of_input_tokens_for_sources,
                self.config.limit_token_sources,
                self.language_model_orchestrator,
                self.chat_history_token_length,
            )

        self.content_reducer = content_reducer

    def _resolve_exposed_params_cls(self) -> type[ExposedParams] | None:
        """Resolve the exposed-params model from the search-engine config, if any."""
        cfg = self.config.search_engine_config
        if isinstance(cfg, BaseSearchEngineConfig):
            return cfg.exposed_params_model()
        return None

    def _tool_context(self) -> WebSearchToolContext:
        return WebSearchToolContext(
            search_engine_config=self.search_engine_service.config,
            date_string=datetime.now().strftime("%A %B %d, %Y"),
            exposed_params_cls=self.exposed_params_cls,
        )

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        ctx = self._tool_context()
        self.tool_parameter_calls = self._mode_strategy.build_tool_parameters(ctx)
        return LanguageModelToolDescription(
            name=self.name,
            description=self._mode_strategy.tool_description(ctx),
            parameters=self.tool_parameter_calls,
        )

    def tool_description_for_system_prompt(self) -> str:
        return self._mode_strategy.system_prompt(self._tool_context())

    def tool_format_information_for_system_prompt(self) -> str:
        return self._mode_strategy.format_information_for_system_prompt(
            default=self.config.tool_format_information_for_system_prompt,
        )

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return self.config.evaluation_check_list

    @override
    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        _LOGGER.info("Running the WebSearch tool")
        start_time = time()
        parameters = self.tool_parameter_calls.model_validate(
            tool_call.arguments,
        )

        screening_service = await self._get_argument_screening_service_if_ff_enabled()

        parameters_dump = parameters.model_dump(by_alias=True)
        debug_info = WebSearchDebugInfo(parameters=parameters_dump)

        web_search_message_logger = WebSearchMessageLogger(
            message_step_logger=self._message_step_logger,
            tool_display_name=self._build_display_name(parameters),
        )
        executor = self._get_executor(
            tool_call, parameters, debug_info, web_search_message_logger
        )

        notify_from_tool_call = self._ff_tool_progress_reporter_callback()
        executor_version = self.config.web_search_mode_config.mode.value

        try:
            if screening_service is not None:
                screening_result = await screening_service(
                    parameters_dump, web_search_message_logger, debug_info=debug_info
                )

                debug_info.steps.append(
                    screening_service.build_step_debug_info_from_result(
                        screening_result
                    )
                )

                if not screening_result.go:
                    return ToolCallResponse(
                        id=tool_call.id,  # type: ignore
                        name=self.name,
                        debug_info=debug_info.model_dump(with_debug_details=self.debug),
                        content=screening_service.build_rejection_response(
                            screening_result
                        ),
                        invocation_stats=debug_info.invocation_stats,
                    )

            with metric_scope(
                tool_duration, tool_errors, executor_version=executor_version
            ):
                content_chunks = await executor.run()

            debug_info.num_chunks_in_final_prompts = len(content_chunks)

            if not content_chunks:
                tool_empty_results.labels(executor_version=executor_version).inc()

            debug_info.execution_time = time() - start_time

            await web_search_message_logger.finished()

            await notify_from_tool_call(
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
                system_reminder=self.config.experimental_features.tool_response_system_reminder.get_reminder_prompt,
                invocation_stats=debug_info.invocation_stats,
            )

        except Exception as e:
            _LOGGER.exception(f"Error executing WebSearch tool: {e}")

            await web_search_message_logger.failed()

            await notify_from_tool_call(
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
                invocation_stats=debug_info.invocation_stats,
            )

    def _get_executor(
        self,
        tool_call: LanguageModelFunction,
        parameters: WebSearchToolParametersInstance,
        debug_info: WebSearchDebugInfo,
        web_search_message_logger: WebSearchMessageLogger,
    ) -> WebSearchExecutor:
        elicitation_service = QueryElicitationService(
            chat_service=self._chat_service,
            display_name=self.display_name(),
            config=self.config.query_elicitation_config,
        )

        services = ExecutorServiceContext(
            search_engine_service=self.search_engine_service,
            crawler_service=self.crawler_service,
            content_processor=self.content_processor,
            language_model_service=self.language_model_service,
            chunk_relevancy_sorter=self.chunk_relevancy_sorter,
        )

        config = ExecutorConfiguration(
            chunk_relevancy_sort_config=self.config.chunk_relevancy_sort_config,
            company_id=self.company_id,
            debug_info=debug_info,
        )

        callbacks = ExecutorCallbacks(
            message_log_callback=web_search_message_logger,
            content_reducer=self.content_reducer,
            query_elicitation=elicitation_service,
            tool_progress_reporter=self._ff_tool_progress_reporter(),
        )

        return self._mode_strategy.build_executor(
            services=services,
            config=config,
            callbacks=callbacks,
            tool_call=tool_call,
            parameters=parameters,
            exposed_params_cls=self.exposed_params_cls,
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

    async def _get_argument_screening_service_if_ff_enabled(
        self,
    ) -> ArgumentScreeningService | None:
        if not feature_flags.enable_web_search_argument_screening_un_18741.is_enabled(
            self.company_id
        ):
            return None

        argument_screening_config = (
            self.config.experimental_features.argument_screening_config
        )
        return ArgumentScreeningService(
            language_model_service=self.language_model_service,
            language_model=argument_screening_config.language_model,
            config=argument_screening_config,
        )

    def _ff_tool_progress_reporter(self):
        if not feature_flags.enable_new_answers_ui_un_14411.is_enabled(self.company_id):
            return self.tool_progress_reporter
        return None

    def _ff_tool_progress_reporter_callback(self):
        async def notify_from_tool_call(
            tool_call: LanguageModelFunction,
            name: str,
            message: str,
            state: ProgressState,
        ):
            if (
                not feature_flags.enable_new_answers_ui_un_14411.is_enabled(
                    self.company_id
                )
                and self.tool_progress_reporter is not None
            ):
                await self.tool_progress_reporter.notify_from_tool_call(
                    tool_call, name, message, state
                )

        return notify_from_tool_call

    def _build_display_name(
        self,
        parameters: WebSearchToolParametersInstance,
    ) -> str:
        return self._mode_strategy.build_display_name(
            base_display_name=self.display_name(),
            parameters=parameters,
        )


ToolFactory.register_tool(WebSearchTool, WebSearchConfig)
