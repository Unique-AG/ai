from functools import partial
from logging import Logger

from unique_internal_search.uploaded_search.service import UploadedSearchTool
from unique_toolkit._common.utils.files import is_image_content
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
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter import (
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
    """Serialize user-uploaded file metadata for model history.

    Every upload is listed, including images and files that were not (or not
    yet, or unsuccessfully) ingested. "Not ingested" only means the file cannot
    be searched with UploadedSearchTool; the raw file is still available to the
    code execution container when that tool is active.
    """
    if load_code_execution_metadata(content) is not None:
        return None

    is_image = is_image_content(content.key)
    kind = "image" if is_image else "file"
    lines = [f"User uploaded {kind}: {content.key} ({content.id})"]

    if content.is_expired():
        lines.append(
            "- Expired due to company retention policy; content can no longer be accessed"
        )
        return "\n".join(lines)

    not_searchable = (
        "; not searchable using UploadedSearchTool" if uploaded_search_available else ""
    )
    if is_image:
        lines.append("- Attached to this message as an image")
    elif content.has_ingestion_failed():
        lines.append(f"- Ingestion failed ({content.ingestion_state}){not_searchable}")
    elif content.is_ingestion_in_progress():
        not_yet_searchable = (
            "; not yet searchable using UploadedSearchTool"
            if uploaded_search_available
            else ""
        )
        lines.append(f"- Ingestion still in progress{not_yet_searchable}")
    elif not content.is_ingested(default_if_unknown=True):
        lines.append(f"- Not ingested{not_searchable}")
    elif uploaded_search_available:
        lines.append("- Searchable using UploadedSearchTool")

    if code_interpreter_available and not content.is_quarantined():
        lines.append(
            "- Available for processing in the code execution container "
            f"(/mnt/data/{content.key})"
        )
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
