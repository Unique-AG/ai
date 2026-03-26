"""Helpers for the experimental OpenFile payload flow (UN-17905).

Extracted from ``unique_ai_builder`` to keep tool-specific wiring
out of the main builder module.
"""

from __future__ import annotations

from datetime import datetime, timezone
from logging import Logger
from typing import TYPE_CHECKING

from unique_toolkit.agentic.history_manager import (
    history_manager as history_manager_module,
)
from unique_toolkit.agentic.history_manager.history_manager import (
    HistoryManager,
    HistoryManagerConfig,
)
from unique_toolkit.agentic.tools.experimental.open_file_tool import OpenFileTool
from unique_toolkit.agentic.tools.tool_manager import (
    ResponsesApiToolManager,
)
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.content import Content

from unique_orchestrator.config import UniqueAIConfig

if TYPE_CHECKING:
    from unique_toolkit.agentic.reference_manager.reference_manager import (
        ReferenceManager,
    )


def handle_uploaded_file_tool_choices(
    config: UniqueAIConfig,
    event: ChatEvent,
    uploaded_documents: list[Content],
    logger: Logger,
) -> None:
    """When send_uploaded_files_in_payload is active, uploaded files are attached
    directly to the LLM context — no InternalSearch needed for them.

    UploadedSearch is intentionally never registered here because the
    open-file tool replaces its functionality.
    """
    if not config.agent.experimental.open_file_tool_config.send_uploaded_files_in_payload:
        return

    now = datetime.now(timezone.utc)
    valid_uploads = [
        doc
        for doc in uploaded_documents
        if doc.expired_at is None or doc.expired_at > now
    ]
    uploaded_pdfs = [d for d in valid_uploads if d.key.lower().endswith(".pdf")]

    if uploaded_pdfs and "InternalSearch" in event.payload.tool_choices:
        event.payload.tool_choices.remove("InternalSearch")
        logger.info(
            "Uploaded PDFs detected (%s files) - removed InternalSearch from forced "
            "tools; PDFs attached directly.",
            len(uploaded_pdfs),
        )

    uploaded_non_pdfs = [d for d in valid_uploads if not d.key.lower().endswith(".pdf")]
    if uploaded_non_pdfs:
        logger.info(
            "Non-PDF uploads detected (%s files) - skipping UploadedSearch; "
            "open-file tool is active.",
            len(uploaded_non_pdfs),
        )


def configure_file_payload(
    config: UniqueAIConfig,
    event: ChatEvent,
    logger: Logger,
    history_manager: HistoryManager,
    reference_manager: ReferenceManager,
    language_model: object,
    tool_manager: ResponsesApiToolManager,
) -> tuple[HistoryManager, list[str]]:
    """Configure file-in-payload handling for the Responses API.

    When sending uploaded files as file parts, disables the UploadedContentConfig
    mechanism so the HistoryManager doesn't also inject uploaded content as text
    (which would duplicate what the input_file parts already provide).

    Also registers the OpenFileTool when send_files_in_payload is enabled,
    backed by a shared registry for agent-requested KB file IDs.

    Returns the (possibly updated) history_manager and the agent file registry.
    """
    if config.agent.experimental.open_file_tool_config.send_uploaded_files_in_payload:
        upload_free_config = HistoryManagerConfig(
            experimental_features=history_manager_module.ExperimentalFeatures(),
            percent_of_max_tokens_for_history=config.agent.input_token_distribution.percent_for_history,
            language_model=config.space.language_model,
            uploaded_content_config=None,
        )
        history_manager = HistoryManager(
            logger,
            event,
            upload_free_config,
            config.space.language_model,
            reference_manager,
        )

    agent_file_registry: list[str] = []

    if config.agent.experimental.open_file_tool_config.send_files_in_payload:
        tool_manager.add_tool(OpenFileTool(event=event, registry=agent_file_registry, config=config.agent.experimental.open_file_tool_config))

    return history_manager, agent_file_registry
