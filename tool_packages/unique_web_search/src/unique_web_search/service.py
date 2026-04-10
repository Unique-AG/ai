import logging
from datetime import datetime
from time import time

from jinja2 import Template
from typing_extensions import override
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

from unique_web_search.config import WebSearchConfig
from unique_web_search.schema import (
    WebSearchDebugInfo,
    WebSearchPlan,
    WebSearchToolParameters,
)
from unique_web_search.services.argument_screening import (
    ArgumentScreeningService,
)
from unique_web_search.services.content_processing import ContentProcessor
from unique_web_search.services.crawlers import get_crawler_service
from unique_web_search.services.executors import (
    WebSearchV1Executor,
    WebSearchV2Executor,
    WebSearchV3Executor,
)
from unique_web_search.services.executors.configs import (
    WebSearchMode,
    WebSearchV3Config,
)
from unique_web_search.services.executors.context import (
    ExecutorCallbacks,
    ExecutorConfiguration,
    ExecutorServiceContext,
)
from unique_web_search.services.message_log import WebSearchMessageLogger
from unique_web_search.services.query_elicitation import QueryElicitationService
from unique_web_search.services.search_engine import (
    SearchEngineMode,
    get_search_engine_mode,
    get_search_engine_service,
)
from unique_web_search.services.search_engine.custom_api import CustomAPIConfig
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
        # TODO (UN-17100): Propagate orchestrator LLM into tool initialization
        self.language_model_orchestrator = (
            language_model_orchestrator or configuration.language_model
        )

        self.search_engine_service = get_search_engine_service(
            self.config.search_engine_config,
            self.language_model_service,
        )
        self.crawler_service = get_crawler_service(self.config.crawler_config)
        self.chunk_relevancy_sorter = ChunkRelevancySorter(self.event)
        self.company_id = self.event.company_id
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

        def content_reducer(web_page_chunks: list[WebPageChunk]) -> list[WebPageChunk]:
            language_model = (
                self.language_model_orchestrator or self.config.language_model
            )

            return reduce_sources_to_token_limit(
                web_page_chunks,
                self.config.language_model_max_input_tokens,
                self.config.percentage_of_input_tokens_for_sources,
                self.config.limit_token_sources,
                language_model,
                self.chat_history_token_length,
            )

        self.content_reducer = content_reducer

    def _resolve_search_engine_mode(self) -> SearchEngineMode:
        """Derive the search-engine mode, respecting CustomAPI overrides."""
        cfg = self.search_engine_service.config
        override = (
            cfg.search_engine_mode
            if isinstance(cfg, CustomAPIConfig)
            else None
        )
        return get_search_engine_mode(cfg.search_engine_name, override=override)

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        if self.config.web_search_mode_config.mode == WebSearchMode.V1:
            self.tool_parameter_calls = WebSearchToolParameters.from_tool_parameter_query_description(
                self.config.web_search_mode_config.tool_parameters_description.query_description,
                self.config.web_search_mode_config.tool_parameters_description.date_restrict_description,
            )
        else:
            engine_mode = self._resolve_search_engine_mode()
            self.tool_parameter_calls = WebSearchPlan.with_search_engine_mode(
                engine_mode
            )

        tool_description = self.config.web_search_mode_config.tool_description

        return LanguageModelToolDescription(
            name=self.name,
            description=tool_description,
            parameters=self.tool_parameter_calls,
        )

    def tool_description_for_system_prompt(self) -> str:
        mode_config = self.config.web_search_mode_config
        if mode_config.mode == WebSearchMode.V1:
            return mode_config.tool_description_for_system_prompt

        engine_mode = self._resolve_search_engine_mode()
        template = Template(mode_config.tool_description_for_system_prompt)

        render_vars: dict[str, object] = {
            "max_steps": mode_config.max_steps,
            "date_string": datetime.now().strftime("%A %B %d, %Y"),
            "search_engine_mode": engine_mode.value,
            "tool_parameters_schema": WebSearchPlan.schema_hint(engine_mode),
            "example_simple": WebSearchPlan.build_example_simple(engine_mode)
            .model_dump_json(indent=2),
            "example_complex": WebSearchPlan.build_example_complex(engine_mode)
            .model_dump_json(indent=2),
        }

        if mode_config.mode == WebSearchMode.V3:
            render_vars["example_fsi"] = (
                WebSearchPlan.build_example_fsi(engine_mode).model_dump_json(indent=2)
            )

        return template.render(**render_vars)

    def tool_format_information_for_system_prompt(self) -> str:
        if self.config.web_search_active_mode == WebSearchMode.V3:
            return self.config.web_search_mode_config_v3.tool_format_information_for_system_prompt
        return self.config.tool_format_information_for_system_prompt

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

        debug_info = WebSearchDebugInfo(parameters=parameters.model_dump())

        web_search_message_logger = WebSearchMessageLogger(
            message_step_logger=self._message_step_logger,
            tool_display_name=self.display_name(),
        )
        executor = self._get_executor(
            tool_call, parameters, debug_info, web_search_message_logger
        )

        notify_from_tool_call = self._ff_tool_progress_reporter_callback()

        try:
            if screening_service is not None:
                screening_result = await screening_service(parameters.model_dump())
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
                    )

            content_chunks = await executor.run()

            debug_info.num_chunks_in_final_prompts = len(content_chunks)

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
            )

    def _get_executor(
        self,
        tool_call: LanguageModelFunction,
        parameters: WebSearchPlan | WebSearchToolParameters,
        debug_info: WebSearchDebugInfo,
        web_search_message_logger: WebSearchMessageLogger,
    ) -> WebSearchV1Executor | WebSearchV2Executor | WebSearchV3Executor:
        # Initialize query elicitation service and get callbacks
        elicitation_service = QueryElicitationService(
            chat_service=self._chat_service,
            display_name=self.display_name(),
            config=self.config.experimental_features.query_elicitation_config,
        )

        # Build context objects
        services = ExecutorServiceContext(
            search_engine_service=self.search_engine_service,
            crawler_service=self.crawler_service,
            content_processor=self.content_processor,
            language_model_service=self.language_model_service,
            chunk_relevancy_sorter=self.chunk_relevancy_sorter,
        )

        config = ExecutorConfiguration(
            language_model=self.config.language_model,
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

        search_config = self.config.web_search_mode_config
        if isinstance(parameters, WebSearchPlan):
            if search_config.mode == WebSearchMode.V3:
                assert isinstance(search_config, WebSearchV3Config)

                return WebSearchV3Executor(
                    services=services,
                    config=config,
                    callbacks=callbacks,
                    tool_call=tool_call,
                    tool_parameters=parameters,
                    max_steps=search_config.max_steps,
                    snippet_judge_config=search_config.snippet_judge_config,
                )
            assert search_config.mode == WebSearchMode.V2
            return WebSearchV2Executor(
                services=services,
                config=config,
                callbacks=callbacks,
                tool_call=tool_call,
                tool_parameters=parameters,
                max_steps=search_config.max_steps,
            )
        elif isinstance(parameters, WebSearchToolParameters):
            assert search_config.mode == WebSearchMode.V1
            return WebSearchV1Executor(
                services=services,
                config=config,
                callbacks=callbacks,
                tool_call=tool_call,
                tool_parameters=parameters,
                refine_query_system_prompt=search_config.refine_query_mode.system_prompt,
                mode=search_config.refine_query_mode.mode,
                max_queries=search_config.max_queries,
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

    async def _get_argument_screening_service_if_ff_enabled(
        self,
    ) -> ArgumentScreeningService | None:
        if not feature_flags.enable_web_search_argument_screening_un_18741.is_enabled(
            self.company_id
        ):
            return None

        return ArgumentScreeningService(
            language_model_service=self.language_model_service,
            language_model=self.config.language_model,
            config=self.config.experimental_features.argument_screening_config,
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


ToolFactory.register_tool(WebSearchTool, WebSearchConfig)
