from datetime import datetime, timezone
from logging import Logger
from typing import NamedTuple, cast

from unique_follow_up_questions.follow_up_postprocessor import (
    FollowUpPostprocessor,
)
from unique_internal_search.uploaded_search.config import (
    UploadedSearchConfig,
)
from unique_internal_search.uploaded_search.service import (
    UploadedSearchTool,
)
from unique_stock_ticker.stock_ticker_postprocessor import (
    StockTickerPostprocessor,
)
from unique_toolkit import LanguageModelService, get_async_openai_client
from unique_toolkit.agentic.debug_info_manager.debug_info_manager import (
    DebugInfoManager,
)
from unique_toolkit.agentic.evaluation.evaluation_manager import EvaluationManager
from unique_toolkit.agentic.evaluation.hallucination.hallucination_evaluation import (
    HallucinationEvaluation,
)
from unique_toolkit.agentic.history_manager import (
    history_manager as history_manager_module,
)
from unique_toolkit.agentic.history_manager.history_manager import (
    HistoryManager,
    HistoryManagerConfig,
)
from unique_toolkit.agentic.loop_runner import (
    BasicLoopIterationRunner,
    BasicLoopIterationRunnerConfig,
    LoopIterationRunner,
    PlanningMiddleware,
    QwenLoopIterationRunner,
    is_qwen_model,
)
from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
from unique_toolkit.agentic.postprocessor.postprocessor_manager import (
    PostprocessorManager,
)
from unique_toolkit.agentic.reference_manager.reference_manager import ReferenceManager
from unique_toolkit.agentic.responses_api import (
    DisplayCodeInterpreterFilesPostProcessor,
    ShowExecutedCodePostprocessor,
)
from unique_toolkit.agentic.thinking_manager.thinking_manager import (
    ThinkingManager,
    ThinkingManagerConfig,
)
from unique_toolkit.agentic.tools.a2a import (
    A2AManager,
    ExtendedSubAgentToolConfig,
    SubAgentDisplaySpec,
    SubAgentEvaluationService,
    SubAgentEvaluationSpec,
    SubAgentReferencesPostprocessor,
    SubAgentResponsesDisplayPostprocessor,
    SubAgentResponsesPostprocessorConfig,
    SubAgentResponseWatcher,
)
from unique_toolkit.agentic.tools.config import ToolBuildConfig
from unique_toolkit.agentic.tools.mcp.manager import MCPManager
from unique_toolkit.agentic.tools.openai_builtin.base import OpenAIBuiltInToolName
from unique_toolkit.agentic.tools.tool_manager import (
    OpenAIBuiltInToolManager,
    ResponsesApiToolManager,
    ToolManager,
    ToolManagerConfig,
)
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent, McpServer
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content import Content
from unique_toolkit.content.service import ContentService
from unique_toolkit.protocols.support import ResponsesSupportCompleteWithReferences

from unique_orchestrator.config import UniqueAIConfig
from unique_orchestrator.unique_ai import UniqueAI


async def build_unique_ai(
    event: ChatEvent,
    logger: Logger,
    config: UniqueAIConfig,
    debug_info_manager: DebugInfoManager,
) -> UniqueAI:
    common_components = _build_common(event, logger, config)

    if config.agent.experimental.responses_api_config.use_responses_api:
        return await _build_responses(
            event=event,
            logger=logger,
            config=config,
            debug_info_manager=debug_info_manager,
            common_components=common_components,
        )
    else:
        return _build_completions(
            event=event,
            logger=logger,
            config=config,
            debug_info_manager=debug_info_manager,
            common_components=common_components,
        )


class _CommonComponents(NamedTuple):
    chat_service: ChatService
    content_service: ContentService
    uploaded_documents: list[Content]
    thinking_manager: ThinkingManager
    reference_manager: ReferenceManager
    history_manager: HistoryManager
    evaluation_manager: EvaluationManager
    postprocessor_manager: PostprocessorManager
    message_step_logger: MessageStepLogger
    response_watcher: SubAgentResponseWatcher
    # Tool Manager Components
    tool_progress_reporter: ToolProgressReporter
    tool_manager_config: ToolManagerConfig
    mcp_manager: MCPManager
    a2a_manager: A2AManager
    mcp_servers: list[McpServer]
    loop_iteration_runner: LoopIterationRunner


def _build_common(
    event: ChatEvent,
    logger: Logger,
    config: UniqueAIConfig,
) -> _CommonComponents:
    chat_service = ChatService(event)

    content_service = ContentService.from_event(event)

    uploaded_documents = content_service.get_documents_uploaded_to_chat()

    response_watcher = SubAgentResponseWatcher()

    tool_progress_reporter = ToolProgressReporter(
        chat_service=chat_service,
        config=config.agent.services.tool_progress_reporter_config,
    )
    thinking_manager_config = ThinkingManagerConfig(
        thinking_steps_display=config.agent.experimental.thinking_steps_display
    )
    thinking_manager = ThinkingManager(
        logger=logger,
        config=thinking_manager_config,
        tool_progress_reporter=tool_progress_reporter,
        chat_service=chat_service,
    )

    reference_manager = ReferenceManager()

    history_manager_config = HistoryManagerConfig(
        experimental_features=history_manager_module.ExperimentalFeatures(),
        percent_of_max_tokens_for_history=config.agent.input_token_distribution.percent_for_history,
        language_model=config.space.language_model,
        uploaded_content_config=config.agent.services.uploaded_content_config,
    )
    history_manager = HistoryManager(
        logger,
        event,
        history_manager_config,
        config.space.language_model,
        reference_manager,
    )

    evaluation_manager = EvaluationManager(logger=logger, chat_service=chat_service)
    if config.agent.services.evaluation_config:
        evaluation_manager.add_evaluation(
            HallucinationEvaluation(
                config.agent.services.evaluation_config.hallucination_config,
                event,
                reference_manager,
            )
        )

    mcp_manager = MCPManager(
        mcp_servers=event.payload.mcp_servers,
        event=event,
        tool_progress_reporter=tool_progress_reporter,
    )
    a2a_manager = A2AManager(
        logger=logger,
        tool_progress_reporter=tool_progress_reporter,
        response_watcher=response_watcher,
    )

    tool_manager_config = ToolManagerConfig(
        tools=config.space.tools,
        max_tool_calls=config.agent.experimental.loop_configuration.max_tool_calls_per_iteration,
    )

    postprocessor_manager = PostprocessorManager(
        logger=logger,
        chat_service=chat_service,
    )

    if config.agent.services.stock_ticker_config is not None:
        postprocessor_manager.add_postprocessor(
            StockTickerPostprocessor(
                config=config.agent.services.stock_ticker_config,
                event=event,
            )
        )

    if (
        config.agent.services.follow_up_questions_config
        and config.agent.services.follow_up_questions_config.number_of_questions > 0
    ):
        # Should run last to make sure the follow up questions are displayed last.
        postprocessor_manager.set_last_postprocessor(
            FollowUpPostprocessor(
                logger=logger,
                config=config.agent.services.follow_up_questions_config,
                event=event,
                historyManager=history_manager,
                llm_service=LanguageModelService.from_event(event),
            )
        )

    loop_iteration_runner = _build_loop_iteration_runner(
        config=config,
        history_manager=history_manager,
        llm_service=LanguageModelService.from_event(event),
        chat_service=chat_service,
    )

    return _CommonComponents(
        chat_service=chat_service,
        content_service=content_service,
        uploaded_documents=uploaded_documents,
        thinking_manager=thinking_manager,
        reference_manager=reference_manager,
        history_manager=history_manager,
        evaluation_manager=evaluation_manager,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
        tool_manager_config=tool_manager_config,
        mcp_servers=event.payload.mcp_servers,
        postprocessor_manager=postprocessor_manager,
        response_watcher=response_watcher,
        message_step_logger=MessageStepLogger(chat_service),
        loop_iteration_runner=loop_iteration_runner,
    )


async def _build_responses(
    event: ChatEvent,
    logger: Logger,
    config: UniqueAIConfig,
    common_components: _CommonComponents,
    debug_info_manager: DebugInfoManager,
) -> UniqueAI:
    client = get_async_openai_client().copy(
        default_headers={
            "x-model": config.space.language_model.name,
            "x-user-id": event.user_id,
            "x-company-id": event.company_id,
            "x-assistant-id": event.payload.assistant_id,
            "x-chat-id": event.payload.chat_id,
        }
    )

    assert config.agent.experimental.responses_api_config is not None

    code_interpreter_config = (
        config.agent.experimental.responses_api_config.code_interpreter
    )
    postprocessor_manager = common_components.postprocessor_manager
    tool_names = [tool.name for tool in config.space.tools]

    if code_interpreter_config is not None:
        if OpenAIBuiltInToolName.CODE_INTERPRETER not in tool_names:
            logger.info("Automatically adding code interpreter to the tools")
            config = config.model_copy(deep=True)
            config.space.tools.append(
                ToolBuildConfig(
                    name=OpenAIBuiltInToolName.CODE_INTERPRETER,
                    configuration=code_interpreter_config.tool_config,
                )
            )
            common_components.tool_manager_config.tools = config.space.tools

        if code_interpreter_config.executed_code_display_config is not None:
            postprocessor_manager.add_postprocessor(
                ShowExecutedCodePostprocessor(
                    config=code_interpreter_config.executed_code_display_config
                )
            )

        postprocessor_manager.add_postprocessor(
            DisplayCodeInterpreterFilesPostProcessor(
                client=client,
                content_service=common_components.content_service,
                config=code_interpreter_config.generated_files_config,
                user_id=event.user_id,
                company_id=event.company_id,
                chat_id=event.payload.chat_id,
                chat_service=common_components.chat_service,
            )
        )

    builtin_tool_manager = await OpenAIBuiltInToolManager.build_manager(
        uploaded_files=common_components.uploaded_documents,
        content_service=common_components.content_service,
        user_id=event.user_id,
        company_id=event.company_id,
        chat_id=event.payload.chat_id,
        client=client,
        tool_configs=config.space.tools,
    )

    tool_manager = ResponsesApiToolManager(
        logger=logger,
        config=common_components.tool_manager_config,
        event=event,
        tool_progress_reporter=common_components.tool_progress_reporter,
        mcp_manager=common_components.mcp_manager,
        a2a_manager=common_components.a2a_manager,
        builtin_tool_manager=builtin_tool_manager,
    )

    postprocessor_manager = common_components.postprocessor_manager

    class ResponsesStreamingHandler(ResponsesSupportCompleteWithReferences):
        def complete_with_references(self, *args, **kwargs):
            return common_components.chat_service.complete_responses_with_references(
                *args, **kwargs
            )

        async def complete_with_references_async(self, *args, **kwargs):
            return await common_components.chat_service.complete_responses_with_references_async(
                *args, **kwargs
            )

    streaming_handler = ResponsesStreamingHandler()

    _add_sub_agents_postprocessor(
        postprocessor_manager=postprocessor_manager,
        tool_manager=tool_manager,
        config=config,
        response_watcher=common_components.response_watcher,
    )
    _add_sub_agents_evaluation(
        evaluation_manager=common_components.evaluation_manager,
        tool_manager=tool_manager,
        config=config,
        event=event,
        response_watcher=common_components.response_watcher,
    )

    return UniqueAI(
        event=event,
        config=config,
        logger=logger,
        chat_service=common_components.chat_service,
        content_service=common_components.content_service,
        tool_manager=tool_manager,
        thinking_manager=common_components.thinking_manager,
        streaming_handler=streaming_handler,
        history_manager=common_components.history_manager,
        reference_manager=common_components.reference_manager,
        evaluation_manager=common_components.evaluation_manager,
        postprocessor_manager=postprocessor_manager,
        debug_info_manager=debug_info_manager,
        message_step_logger=common_components.message_step_logger,
        mcp_servers=event.payload.mcp_servers,
        loop_iteration_runner=common_components.loop_iteration_runner,
    )


def _build_completions(
    event: ChatEvent,
    logger: Logger,
    config: UniqueAIConfig,
    common_components: _CommonComponents,
    debug_info_manager: DebugInfoManager,
) -> UniqueAI:
    # Uploaded content behavior is always to force uploaded search tool:
    # 1. Add it to forced tools if there are tool choices.
    # 2. Simply force it if there are no tool choices.
    # 3. Not available if not uploaded documents.
    now = datetime.now(timezone.utc)
    UPLOADED_DOCUMENTS_VALID = [
        doc
        for doc in common_components.uploaded_documents
        if doc.expired_at is None or doc.expired_at > now
    ]
    UPLOADED_DOCUMENTS_EXPIRED = [
        doc
        for doc in common_components.uploaded_documents
        if doc.expired_at is not None and doc.expired_at <= now
    ]
    TOOL_CHOICES = len(event.payload.tool_choices) > 0

    if UPLOADED_DOCUMENTS_EXPIRED:
        logger.info(
            f"Number of expired uploaded documents: {len(UPLOADED_DOCUMENTS_EXPIRED)}"
        )

    if UPLOADED_DOCUMENTS_VALID:
        logger.info(
            f"Number of valid uploaded documents: {len(UPLOADED_DOCUMENTS_VALID)}"
        )
        common_components.tool_manager_config.tools.append(
            ToolBuildConfig(
                name=UploadedSearchTool.name,
                display_name=UploadedSearchTool.name,
                configuration=UploadedSearchConfig(),
            )
        )
    if TOOL_CHOICES and UPLOADED_DOCUMENTS_VALID:
        event.payload.tool_choices.append(str(UploadedSearchTool.name))

    tool_manager = ToolManager(
        logger=logger,
        config=common_components.tool_manager_config,
        event=event,
        tool_progress_reporter=common_components.tool_progress_reporter,
        mcp_manager=common_components.mcp_manager,
        a2a_manager=common_components.a2a_manager,
    )
    if not TOOL_CHOICES and UPLOADED_DOCUMENTS_VALID:
        tool_manager.add_forced_tool(UploadedSearchTool.name)

    postprocessor_manager = common_components.postprocessor_manager

    _add_sub_agents_postprocessor(
        postprocessor_manager=postprocessor_manager,
        tool_manager=tool_manager,
        config=config,
        response_watcher=common_components.response_watcher,
    )
    _add_sub_agents_evaluation(
        evaluation_manager=common_components.evaluation_manager,
        tool_manager=tool_manager,
        config=config,
        event=event,
        response_watcher=common_components.response_watcher,
    )

    return UniqueAI(
        event=event,
        config=config,
        logger=logger,
        chat_service=common_components.chat_service,
        content_service=common_components.content_service,
        tool_manager=tool_manager,
        thinking_manager=common_components.thinking_manager,
        history_manager=common_components.history_manager,
        reference_manager=common_components.reference_manager,
        streaming_handler=common_components.chat_service,
        evaluation_manager=common_components.evaluation_manager,
        postprocessor_manager=postprocessor_manager,
        debug_info_manager=debug_info_manager,
        mcp_servers=event.payload.mcp_servers,
        message_step_logger=common_components.message_step_logger,
        loop_iteration_runner=common_components.loop_iteration_runner,
    )


def _add_sub_agents_postprocessor(
    postprocessor_manager: PostprocessorManager,
    tool_manager: ToolManager | ResponsesApiToolManager,
    config: UniqueAIConfig,
    response_watcher: SubAgentResponseWatcher,
) -> None:
    sub_agents = tool_manager.sub_agents
    if len(sub_agents) > 0:
        display_config = SubAgentResponsesPostprocessorConfig(
            sleep_time_before_update=config.agent.experimental.sub_agents_config.sleep_time_before_update,
        )
        display_specs = []
        for tool in sub_agents:
            tool_config = cast(
                ExtendedSubAgentToolConfig, tool.settings.configuration
            )  # (BeforeValidator of ToolBuildConfig)

            display_specs.append(
                SubAgentDisplaySpec(
                    assistant_id=tool_config.assistant_id,
                    display_name=tool.display_name(),
                    display_config=tool_config.response_display_config,
                )
            )
        reference_postprocessor = SubAgentReferencesPostprocessor(
            response_watcher=response_watcher,
        )
        sub_agent_responses_postprocessor = SubAgentResponsesDisplayPostprocessor(
            config=display_config,
            response_watcher=response_watcher,
            display_specs=display_specs,
        )
        postprocessor_manager.add_postprocessor(reference_postprocessor)
        postprocessor_manager.add_postprocessor(sub_agent_responses_postprocessor)


def _add_sub_agents_evaluation(
    evaluation_manager: EvaluationManager,
    tool_manager: ToolManager | ResponsesApiToolManager,
    config: UniqueAIConfig,
    event: ChatEvent,
    response_watcher: SubAgentResponseWatcher,
) -> None:
    sub_agents = tool_manager.sub_agents
    if (
        len(sub_agents) > 0
        and config.agent.experimental.sub_agents_config.evaluation_config is not None
    ):
        evaluation_specs = []
        for tool in sub_agents:
            tool_config = cast(
                ExtendedSubAgentToolConfig, tool.settings.configuration
            )  # (BeforeValidator of ToolBuildConfig)

            evaluation_specs.append(
                SubAgentEvaluationSpec(
                    assistant_id=tool_config.assistant_id,
                    display_name=tool.display_name(),
                    config=tool_config.evaluation_config,
                )
            )

        sub_agent_evaluation = SubAgentEvaluationService(
            config=config.agent.experimental.sub_agents_config.evaluation_config,
            language_model_service=LanguageModelService.from_event(event),
            evaluation_specs=evaluation_specs,
            response_watcher=response_watcher,
        )
        evaluation_manager.add_evaluation(sub_agent_evaluation)


def _build_loop_iteration_runner(
    config: UniqueAIConfig,
    history_manager: HistoryManager,
    llm_service: LanguageModelService,
    chat_service: ChatService,
) -> LoopIterationRunner:
    runner = BasicLoopIterationRunner(
        config=BasicLoopIterationRunnerConfig(
            max_loop_iterations=config.agent.max_loop_iterations
        )
    )

    if is_qwen_model(model=config.space.language_model):
        runner = QwenLoopIterationRunner(
            qwen_forced_tool_call_instruction=config.agent.experimental.loop_configuration.model_specific.qwen.forced_tool_call_instruction,
            qwen_last_iteration_instruction=config.agent.experimental.loop_configuration.model_specific.qwen.last_iteration_instruction,
            max_loop_iterations=config.agent.max_loop_iterations,
            chat_service=chat_service,
        )

    if config.agent.experimental.loop_configuration.planning_config is not None:
        runner = PlanningMiddleware(
            loop_runner=runner,
            config=config.agent.experimental.loop_configuration.planning_config,
            history_manager=history_manager,
            llm_service=llm_service,
        )

    return runner
