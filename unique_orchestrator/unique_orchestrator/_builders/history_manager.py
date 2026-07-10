from functools import partial
from logging import Logger

from unique_internal_search.uploaded_search.service import UploadedSearchTool
from unique_toolkit.agentic.history_manager import (
    history_manager as history_manager_module,
)
from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
    FileContentSerializer,
)
from unique_toolkit.agentic.history_manager.history_manager import (
    HistoryManager,
    HistoryManagerConfig,
)
from unique_toolkit.agentic.reference_manager.reference_manager import ReferenceManager
from unique_toolkit.agentic.tools.openai_builtin.base import OpenAIBuiltInToolName
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.activator import (
    CodeInterpreterActivatorTool,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.artifacts import (
    load_code_execution_metadata,
)
from unique_toolkit.agentic.tools.tool_manager import (
    ResponsesApiToolManager,
    ToolManager,
)
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.content import Content

from unique_orchestrator.config import UniqueAIConfig


def serialize_uploaded_file_for_history(
    content: Content,
    *,
    uploaded_search_available: bool,
    code_interpreter_available: bool,
) -> str | None:
    """Serialize user-uploaded file metadata for model history."""
    if load_code_execution_metadata(content) is not None:
        return None

    lines = [f"User uploaded file: {content.key} ({content.id})"]
    if (
        uploaded_search_available
        and content.is_ingested(default_if_unknown=True)
        and not content.is_expired()
    ):
        lines.append("- Searchable using UploadedSearchTool")
    if code_interpreter_available:
        lines.append("- Available for processing in the code execution container")
    return "\n".join(lines)


def _get_file_content_serializer(
    config: UniqueAIConfig,
    tool_manager: ToolManager | ResponsesApiToolManager,
) -> FileContentSerializer | None:
    if not config.agent.input_token_distribution.serialize_uploaded_files_in_user_message:
        return None

    return partial(
        serialize_uploaded_file_for_history,
        uploaded_search_available=(
            tool_manager.get_tool_by_name(UploadedSearchTool.name) is not None
        ),
        code_interpreter_available=(
            tool_manager.get_tool_by_name(OpenAIBuiltInToolName.CODE_INTERPRETER)
            is not None
            or tool_manager.get_tool_by_name(CodeInterpreterActivatorTool.NAME)
            is not None
        ),
    )


def build_history_manager(
    *,
    event: ChatEvent,
    logger: Logger,
    config: UniqueAIConfig,
    reference_manager: ReferenceManager,
    tool_manager: ToolManager | ResponsesApiToolManager,
) -> HistoryManager:
    """Build a history manager after the active tools are known."""
    history_manager_config = HistoryManagerConfig(
        experimental_features=history_manager_module.ExperimentalFeatures(),
        percent_of_max_tokens_for_history=config.agent.input_token_distribution.percent_for_history,
        language_model=config.space.language_model,
        uploaded_content_config=config.agent.services.uploaded_content_config,
        enable_tool_call_persistence=config.agent.input_token_distribution.enable_tool_call_persistence,
    )
    return HistoryManager(
        logger,
        event,
        history_manager_config,
        config.space.language_model,
        reference_manager,
        file_content_serializer=_get_file_content_serializer(
            config=config,
            tool_manager=tool_manager,
        ),
    )
