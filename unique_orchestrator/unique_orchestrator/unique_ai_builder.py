import os
from logging import Logger
from typing import NamedTuple

from openai import AsyncOpenAI
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
from unique_toolkit.agentic.postprocessor.postprocessor_manager import (
    Postprocessor,
    PostprocessorManager,
)
from unique_toolkit.agentic.reference_manager.reference_manager import ReferenceManager
from unique_toolkit.agentic.responses_api import (
    DisplayCodeInterpreterFilesPostProcessor,
    DisplayCodeInterpreterFilesPostProcessorConfig,
    ShowExecutedCodePostprocessor,
)
from unique_toolkit.agentic.thinking_manager.thinking_manager import (
    ThinkingManager,
    ThinkingManagerConfig,
)
from unique_toolkit.agentic.tools.a2a import (
    A2AManager,
    ExtendedSubAgentToolConfig,
    SubAgentEvaluationService,
    SubAgentResponsesPostprocessor,
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
from unique_orchestrator.unique_ai import UniqueAI, UniqueAIResponsesApi


async def build_unique_ai(
    event: ChatEvent,
    logger: Logger,
    config: UniqueAIConfig,
    debug_info_manager: DebugInfoManager,
) -> UniqueAI | UniqueAIResponsesApi:
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
    # Tool Manager Components
    tool_progress_reporter: ToolProgressReporter
    tool_manager_config: ToolManagerConfig
    mcp_manager: MCPManager
    a2a_manager: A2AManager
    mcp_servers: list[McpServer]
    postprocessors: list[Postprocessor]


def _build_common(
    event: ChatEvent,
    logger: Logger,
    config: UniqueAIConfig,
) -> _CommonComponents:
    chat_service = ChatService(event)

    content_service = ContentService.from_event(event)

    uploaded_documents = content_service.get_documents_uploaded_to_chat()

    tool_progress_reporter = ToolProgressReporter(chat_service=chat_service)
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
        experimental_features=history_manager_module.ExperimentalFeatures(
            full_sources_serialize_dump=False,
        ),
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
    )
    tool_manager_config = ToolManagerConfig(
        tools=config.space.tools,
        max_tool_calls=config.agent.experimental.loop_configuration.max_tool_calls_per_iteration,
    )

    postprocessors = []

    if config.agent.services.stock_ticker_config:
        postprocessors.append(
            StockTickerPostprocessor(
                config=config.agent.services.stock_ticker_config,
                event=event,
            )
        )

    if (
        config.agent.services.follow_up_questions_config
        and config.agent.services.follow_up_questions_config.number_of_questions > 0
    ):
        postprocessors.append(
            FollowUpPostprocessor(
                logger=logger,
                config=config.agent.services.follow_up_questions_config,
                event=event,
                historyManager=history_manager,
                llm_service=LanguageModelService.from_event(event),
            )
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
        postprocessors=postprocessors,
    )


def _prepare_base_url(url: str, use_v1: bool) -> str:
    url = url.rstrip("/") + "/openai"

    if use_v1:
        url += "/v1"

    return url


def _get_openai_client_from_env(
    config: UniqueAIConfig, use_v1: bool = False
) -> AsyncOpenAI:
    use_direct_azure_client = (
        config.agent.experimental.responses_api_config.use_direct_azure_client
    )
    api_key_env_var = config.agent.experimental.responses_api_config.direct_azure_client_api_key_env_var
    api_base_env_var = config.agent.experimental.responses_api_config.direct_azure_client_api_base_env_var

    if use_direct_azure_client:
        # TODO: (for testing only), remove when v1 endpoint is working
        return AsyncOpenAI(
            api_key=os.environ[api_key_env_var],
            base_url=_prepare_base_url(os.environ[api_base_env_var], use_v1=use_v1),
        )
    else:
        return get_async_openai_client().copy(
            default_headers={
                "x-model": config.space.language_model.name
            }  # Backend requires a model name
        )


async def _build_responses(
    event: ChatEvent,
    logger: Logger,
    config: UniqueAIConfig,
    common_components: _CommonComponents,
    debug_info_manager: DebugInfoManager,
) -> UniqueAIResponsesApi:
    client = _get_openai_client_from_env(config, use_v1=True)
    code_interpreter_config = (
        config.agent.experimental.responses_api_config.code_interpreter
    )

    tool_names = [tool.name for tool in config.space.tools]
    if (
        code_interpreter_config is not None
        and OpenAIBuiltInToolName.CODE_INTERPRETER not in tool_names
    ):
        logger.info("Automatically adding code interpreter to the tools")
        config = config.model_copy(deep=True)
        config.space.tools.append(
            ToolBuildConfig(
                name=OpenAIBuiltInToolName.CODE_INTERPRETER,
                configuration=code_interpreter_config,
            )
        )
        common_components.tool_manager_config.tools = config.space.tools

    builtin_tool_manager = OpenAIBuiltInToolManager(
        uploaded_files=common_components.uploaded_documents,
        chat_id=event.payload.chat_id,
        content_service=common_components.content_service,
        user_id=event.user_id,
        company_id=event.company_id,
        client=client,
    )

    tool_manager = await ResponsesApiToolManager.build_manager(
        logger=logger,
        config=common_components.tool_manager_config,
        event=event,
        tool_progress_reporter=common_components.tool_progress_reporter,
        mcp_manager=common_components.mcp_manager,
        a2a_manager=common_components.a2a_manager,
        builtin_tool_manager=builtin_tool_manager,
    )

    postprocessor_manager = PostprocessorManager(
        logger=logger,
        chat_service=common_components.chat_service,
    )
    for postprocessor in common_components.postprocessors:
        postprocessor_manager.add_postprocessor(postprocessor)

    if (
        config.agent.experimental.responses_api_config.code_interpreter_display_config
        is not None
    ):
        postprocessor_manager.add_postprocessor(
            ShowExecutedCodePostprocessor(
                config=config.agent.experimental.responses_api_config.code_interpreter_display_config
            )
        )

    postprocessor_manager.add_postprocessor(
        DisplayCodeInterpreterFilesPostProcessor(
            client=client,
            content_service=common_components.content_service,
            config=DisplayCodeInterpreterFilesPostProcessorConfig(
                upload_scope_id=config.agent.experimental.responses_api_config.generated_files_scope_id,
            ),
        )
    )

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
        user_id=event.user_id,
        company_id=event.company_id,
        chat_id=event.payload.chat_id,
    )
    _add_sub_agents_evaluation(
        evaluation_manager=common_components.evaluation_manager,
        tool_manager=tool_manager,
        config=config,
        event=event,
    )

    return UniqueAIResponsesApi(
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
        mcp_servers=event.payload.mcp_servers,
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
    UPLOADED_DOCUMENTS = len(common_components.uploaded_documents) > 0
    TOOL_CHOICES = len(event.payload.tool_choices) > 0
    if UPLOADED_DOCUMENTS:
        logger.info(
            f"Adding UploadedSearchTool with {len(common_components.uploaded_documents)} documents"
        )
        common_components.tool_manager_config.tools.append(
            ToolBuildConfig(
                name=UploadedSearchTool.name,
                display_name=UploadedSearchTool.name,
                configuration=UploadedSearchConfig(),
            )
        )
    if TOOL_CHOICES and UPLOADED_DOCUMENTS:
        event.payload.tool_choices.append(str(UploadedSearchTool.name))

    tool_manager = ToolManager(
        logger=logger,
        config=common_components.tool_manager_config,
        event=event,
        tool_progress_reporter=common_components.tool_progress_reporter,
        mcp_manager=common_components.mcp_manager,
        a2a_manager=common_components.a2a_manager,
    )
    if not TOOL_CHOICES and UPLOADED_DOCUMENTS:
        tool_manager.add_forced_tool(UploadedSearchTool.name)

    postprocessor_manager = PostprocessorManager(
        logger=logger,
        chat_service=common_components.chat_service,
    )
    for postprocessor in common_components.postprocessors:
        postprocessor_manager.add_postprocessor(postprocessor)

    _add_sub_agents_postprocessor(
        postprocessor_manager=postprocessor_manager,
        tool_manager=tool_manager,
        user_id=event.user_id,
        company_id=event.company_id,
        chat_id=event.payload.chat_id,
    )
    _add_sub_agents_evaluation(
        evaluation_manager=common_components.evaluation_manager,
        tool_manager=tool_manager,
        config=config,
        event=event,
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
    )


def _add_sub_agents_postprocessor(
    postprocessor_manager: PostprocessorManager,
    tool_manager: ToolManager | ResponsesApiToolManager,
    user_id: str,
    company_id: str,
    chat_id: str,
) -> None:
    sub_agents = tool_manager.sub_agents
    if len(sub_agents) > 0:
        sub_agent_responses_postprocessor = SubAgentResponsesPostprocessor(
            user_id=user_id,
            main_agent_chat_id=chat_id,
            company_id=company_id,
        )
        postprocessor_manager.add_postprocessor(sub_agent_responses_postprocessor)

        for tool in tool_manager.sub_agents:
            assert isinstance(tool.config, ExtendedSubAgentToolConfig)
            sub_agent_responses_postprocessor.register_sub_agent_tool(
                tool, tool.config.response_display_config
            )


def _add_sub_agents_evaluation(
    evaluation_manager: EvaluationManager,
    tool_manager: ToolManager | ResponsesApiToolManager,
    config: UniqueAIConfig,
    event: ChatEvent,
) -> None:
    sub_agents = tool_manager.sub_agents
    if len(sub_agents) > 0:
        sub_agent_evaluation = None
        if config.agent.experimental.sub_agents_config.evaluation_config is not None:
            sub_agent_evaluation = SubAgentEvaluationService(
                config=config.agent.experimental.sub_agents_config.evaluation_config,
                language_model_service=LanguageModelService.from_event(event),
            )
            evaluation_manager.add_evaluation(sub_agent_evaluation)
            for tool in tool_manager.sub_agents:
                assert isinstance(tool.config, ExtendedSubAgentToolConfig)
                sub_agent_evaluation.register_sub_agent_tool(
                    tool, tool.config.evaluation_config
                )
