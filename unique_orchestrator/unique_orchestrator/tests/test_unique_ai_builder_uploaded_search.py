import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest
from tests.test_obj_factory import get_event_obj
from unique_internal_search.uploaded_search.service import UploadedSearchTool
from unique_toolkit.agentic.tools.a2a import SubAgentResponseWatcher
from unique_toolkit.agentic.tools.a2a.manager import A2AManager
from unique_toolkit.agentic.tools.mcp.manager import MCPManager
from unique_toolkit.agentic.tools.openai_builtin.manager import OpenAIBuiltInToolManager
from unique_toolkit.agentic.tools.tool_manager import (
    ResponsesApiToolManager,
    ToolManagerConfig,
)
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.chat.service import ChatService

from unique_orchestrator.unique_ai_builder import (
    _CommonComponents,
    _handle_uploaded_pdf_tool_choices,
)


@pytest.mark.ai
def test_handle_uploaded_pdf_tool_choices__registers_uploaded_search_before_forcing() -> (
    None
):
    """Ensure UploadedSearch is registered before forcing it in responses mode."""
    event = get_event_obj(
        user_id="test_user",
        company_id="test_company",
        assistant_id="test_assistant",
        chat_id="test_chat",
    )
    logger = logging.getLogger(__name__)
    config = MagicMock()
    config.agent.experimental.open_pdf_tool_config.send_uploaded_pdf_in_payload = True

    tool_progress_reporter = ToolProgressReporter(Mock(spec=ChatService))
    tool_manager_config = ToolManagerConfig(tools=[])
    common_components = _CommonComponents(
        chat_service=Mock(spec=ChatService),
        content_service=Mock(),
        llm_service=Mock(),
        uploaded_documents=[SimpleNamespace(key="notes.txt", expired_at=None)],
        thinking_manager=Mock(),
        reference_manager=Mock(),
        history_manager=Mock(),
        evaluation_manager=Mock(),
        postprocessor_manager=Mock(),
        message_step_logger=Mock(),
        response_watcher=SubAgentResponseWatcher(),
        tool_progress_reporter=tool_progress_reporter,
        tool_manager_config=tool_manager_config,
        mcp_manager=MCPManager(
            mcp_servers=[],
            event=event,
            tool_progress_reporter=tool_progress_reporter,
        ),
        a2a_manager=A2AManager(
            logger=logger,
            tool_progress_reporter=tool_progress_reporter,
            response_watcher=SubAgentResponseWatcher(),
        ),
        mcp_servers=[],
    )

    has_non_pdf_uploads = _handle_uploaded_pdf_tool_choices(
        config=config,
        event=event,
        common_components=common_components,
        logger=logger,
    )

    mock_builtin_manager = Mock(spec=OpenAIBuiltInToolManager)
    mock_builtin_manager.get_all_openai_builtin_tools.return_value = []
    tool_manager = ResponsesApiToolManager(
        logger=logger,
        config=tool_manager_config,
        event=event,
        tool_progress_reporter=tool_progress_reporter,
        mcp_manager=common_components.mcp_manager,
        a2a_manager=common_components.a2a_manager,
        builtin_tool_manager=mock_builtin_manager,
    )

    assert has_non_pdf_uploads is True
    assert tool_manager.get_tool_by_name(UploadedSearchTool.name) is not None
    assert UploadedSearchTool.name not in event.payload.tool_choices

    tool_manager.add_forced_tool(UploadedSearchTool.name)

    assert UploadedSearchTool.name in event.payload.tool_choices
