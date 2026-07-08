import logging
import re
from datetime import datetime
from time import time

from jinja2 import Template
from typing_extensions import override
from unique_search_proxy_core.search_engines.call_schema import (
    build_exposed_tool_field_defs,
    exposed_field_names,
)
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
from unique_web_search.services.executors import (
    WebSearchMode,
    WebSearchV1Executor,
    WebSearchV2Executor,
    WebSearchV3Config,
    WebSearchV3Executor,
)
from unique_web_search.services.executors.context import (
    ExecutorCallbacks,
    ExecutorConfiguration,
    ExecutorServiceContext,
)
from unique_web_search.services.executors.v1.schema import WebSearchToolParameters
from unique_web_search.services.executors.v2.schema import WebSearchPlan
from unique_web_search.services.executors.v3.schema import WebSearchV3ToolParameters
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
        # TODO (UN-17100): Propagate orchestrator LLM into tool initialization.
        # Until then, fall back to the per-tool token-counting model.
        self.language_model_orchestrator = (
            language_model_orchestrator or configuration.token_counting_language_model
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

            return reduce_sources_to_token_limit(
                web_page_chunks,
                self.config.language_model_max_input_tokens,
                self.config.percentage_of_input_tokens_for_sources,
                self.config.limit_token_sources,
                self.language_model_orchestrator,
                self.chat_history_token_length,
            )

        self.content_reducer = content_reducer

    def _resolve_search_engine_mode(self) -> SearchEngineMode:
        """Derive the search-engine mode, respecting CustomAPI overrides."""
        cfg = self.search_engine_service.config
        override = cfg.search_engine_mode if isinstance(cfg, CustomAPIConfig) else None
        return get_search_engine_mode(cfg.engine, override=override)

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        if self.config.web_search_mode_config.mode == WebSearchMode.V1:
            exposed_field_defs = build_exposed_tool_field_defs(
                self.search_engine_service.config
            )
            self.tool_parameter_calls = WebSearchToolParameters.with_exposed_fields(
                exposed_field_defs,
                query_description=(
                    self.config.web_search_mode_config.tool_parameters_description.query_description
                ),
            )
        elif self.config.web_search_mode_config.mode == WebSearchMode.V3:
            exposed_field_defs = build_exposed_tool_field_defs(
                self.search_engine_service.config
            )
            self._exposed_field_names = exposed_field_names(
                self.search_engine_service.config
            )
            self.tool_parameter_calls = WebSearchV3ToolParameters.with_exposed_fields(
                exposed_field_defs
            )
            tool_description = Template(
                self.config.web_search_mode_config.tool_description
            ).render(
                tool_parameters_schema=WebSearchV3ToolParameters.schema_hint(
                    exposed_field_defs
                ),
            )
        else:
            engine_mode = self._resolve_search_engine_mode()
            self.tool_parameter_calls = WebSearchPlan.with_search_engine_mode(
                engine_mode
            )
            tool_description = self.config.web_search_mode_config.tool_description

        if self.config.web_search_mode_config.mode != WebSearchMode.V3:
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

        template_str = mode_config.tool_description_for_system_prompt

        if mode_config.mode == WebSearchMode.V3:
            return Template(template_str).render(
                date_string=datetime.now().strftime("%A %B %d, %Y"),
            )

        # Backwards compatibility: V2 prompts persisted before the Jinja
        # migration use the legacy ``$max_steps`` placeholder. Jinja would
        # otherwise pass it through verbatim, so rewrite it to the Jinja
        # equivalent before rendering.
        if "$max_steps" in template_str:
            _LOGGER.warning(
                "V2 web-search prompt contains legacy '$max_steps' placeholder; "
                "rewriting to '{{ max_steps }}'. Please update the stored "
                "configuration to use Jinja syntax."
            )
            template_str = template_str.replace("$max_steps", "{{ max_steps }}")

        engine_mode = self._resolve_search_engine_mode()
        return Template(template_str).render(
            max_steps=mode_config.max_steps,
            date_string=datetime.now().strftime("%A %B %d, %Y"),
            search_engine_mode=engine_mode.value,
            tool_parameters_schema=WebSearchPlan.schema_hint(engine_mode),
            example_simple=WebSearchPlan.build_example_simple(
                engine_mode
            ).model_dump_json(indent=2),
            example_complex=WebSearchPlan.build_example_complex(
                engine_mode
            ).model_dump_json(indent=2),
        )

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

        parameters_dump = parameters.model_dump()
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
                    parameters_dump, web_search_message_logger
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
        parameters: WebSearchPlan | WebSearchToolParameters | WebSearchV3ToolParameters,
        debug_info: WebSearchDebugInfo,
        web_search_message_logger: WebSearchMessageLogger,
    ) -> WebSearchV1Executor | WebSearchV2Executor | WebSearchV3Executor:
        # Initialize query elicitation service and get callbacks
        elicitation_service = QueryElicitationService(
            chat_service=self._chat_service,
            display_name=self.display_name(),
            config=self.config.query_elicitation_config,
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
        if search_config.mode == WebSearchMode.V3:
            assert isinstance(search_config, WebSearchV3Config)
            assert isinstance(parameters, WebSearchV3ToolParameters)

            return WebSearchV3Executor(
                services=services,
                config=config,
                callbacks=callbacks,
                tool_call=tool_call,
                tool_parameters=parameters,
            )
        if isinstance(parameters, WebSearchPlan):
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
                refine_query_language_model=search_config.refine_query_mode.language_model,
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
        parameters: WebSearchPlan | WebSearchToolParameters | WebSearchV3ToolParameters,
    ) -> str:
        if not isinstance(parameters, WebSearchV3ToolParameters):
            return self.display_name()

        display_name = self.display_name()
        # Remove "search" from the display name (case-insensitive, all occurrences).
        display_name = re.sub(
            r"\bsearch\b", "", display_name, flags=re.IGNORECASE
        ).strip()

        suffix = parameters.get_display_name_suffix()

        return display_name + suffix


ToolFactory.register_tool(WebSearchTool, WebSearchConfig)
