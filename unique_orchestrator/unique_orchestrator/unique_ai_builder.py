from logging import Logger

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
from unique_toolkit import LanguageModelService
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.service import ContentService
from unique_toolkit.agentic.debug_info_manager.debug_info_manager import (
    DebugInfoManager,
)
from unique_toolkit.agentic.evaluation.evaluation_manager import EvaluationManager
from unique_toolkit.agentic.evaluation.hallucination.hallucination_evaluation import (
    HallucinationEvaluation,
)
from  unique_toolkit.agentic.history_manager import (
    history_manager as history_manager_module,
)
from  unique_toolkit.agentic.history_manager.history_manager import (
    HistoryManager,
    HistoryManagerConfig,
)
from unique_toolkit.agentic.postprocessor.postprocessor_manager import (
    PostprocessorManager,
)
from unique_toolkit.agentic.reference_manager.reference_manager import ReferenceManager
from unique_toolkit.agentic.thinking_manager.thinking_manager import (
    ThinkingManager,
    ThinkingManagerConfig,
)
from unique_toolkit.agentic.tools.a2a.manager import A2AManager
from unique_toolkit.agentic.tools.config import ToolBuildConfig
from unique_toolkit.agentic.tools.mcp.manager import MCPManager
from unique_toolkit.agentic.tools.tool_manager import ToolManager, ToolManagerConfig
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter

from unique_orchestrator.config import UniqueAIConfig
from unique_orchestrator.unique_ai import UniqueAI


def build_unique_ai(
    event: ChatEvent,
    logger: Logger,
    config: UniqueAIConfig,
    debug_info_manager: DebugInfoManager,
) -> UniqueAI:
    chat_service = ChatService(event)

    content_service = ContentService.from_event(event)
    tool_progress_reporter = ToolProgressReporter(chat_service=chat_service)
    reference_manager = ReferenceManager()
    thinking_manager_config = ThinkingManagerConfig(
        thinking_steps_display=config.agent.experimental.thinking_steps_display
    )

    thinking_manager = ThinkingManager(
        logger=logger,
        config=thinking_manager_config,
        tool_progress_reporter=tool_progress_reporter,
        chat_service=chat_service,
    )

    uploaded_documents = content_service.get_documents_uploaded_to_chat()
    if len(uploaded_documents) > 0:
        logger.info(
            f"Adding UploadedSearchTool with {len(uploaded_documents)} documents"
        )
        config.space.tools.append(
            ToolBuildConfig(
                name=UploadedSearchTool.name,
                display_name=UploadedSearchTool.name,
                configuration=UploadedSearchConfig(),
            ),
        )
        event.payload.tool_choices.append(str(UploadedSearchTool.name))

    mcp_manager = MCPManager(
        mcp_servers=event.payload.mcp_servers,
        event=event,
        tool_progress_reporter=tool_progress_reporter,
    )

    a2a_manager = A2AManager(
        logger=logger,
        tool_progress_reporter=tool_progress_reporter,
    )

    tool_config = ToolManagerConfig(
        tools=config.space.tools,
        max_tool_calls=config.agent.experimental.loop_configuration.max_tool_calls_per_iteration,
    )

    tool_manager = ToolManager(
        logger=logger,
        config=tool_config,
        event=event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

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

    postprocessor_manager = PostprocessorManager(
        logger=logger,
        chat_service=chat_service,
    )

    if config.agent.services.stock_ticker_config:
        postprocessor_manager.add_postprocessor(
            StockTickerPostprocessor(
                config=config.agent.services.stock_ticker_config,
                event=event,
            )
        )

    if config.agent.services.follow_up_questions_config:
        postprocessor_manager.add_postprocessor(
            FollowUpPostprocessor(
                logger=logger,
                config=config.agent.services.follow_up_questions_config,
                event=event,
                historyManager=history_manager,
                llm_service=LanguageModelService.from_event(event),
            )
        )

    return UniqueAI(
        event=event,
        config=config,
        logger=logger,
        chat_service=chat_service,
        content_service=content_service,
        tool_manager=tool_manager,
        thinking_manager=thinking_manager,
        history_manager=history_manager,
        reference_manager=reference_manager,
        evaluation_manager=evaluation_manager,
        postprocessor_manager=postprocessor_manager,
        debug_info_manager=debug_info_manager,
        mcp_servers=event.payload.mcp_servers,
    )
