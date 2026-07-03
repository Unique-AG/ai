"""Regression tests for shared ChatService injection into tools (UN-19148).

These tests validate that services flow through the immutable
``ToolExecutionContext`` rather than being captured (and thus going stale) at
tool-construction time. In particular, mutating ``chat_service`` (e.g. the
live assistant message id) between tool construction and tool execution must
be visible inside ``run()``/``prepare()`` because ``ctx.chat_service`` is
always the same live instance.
"""

import asyncio
from unittest.mock import Mock

import pytest

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.a2a import A2AManager
from unique_toolkit.agentic.tools.a2a.response_watcher import SubAgentResponseWatcher
from unique_toolkit.agentic.tools.config import (
    ToolBuildConfig,
    ToolIcon,
    ToolSelectionPolicy,
)
from unique_toolkit.agentic.tools.execution_context import ToolExecutionContext
from unique_toolkit.agentic.tools.mcp.manager import MCPManager
from unique_toolkit.agentic.tools.mcp.models import MCPToolConfig
from unique_toolkit.agentic.tools.mcp.tool_wrapper import MCPToolWrapper
from unique_toolkit.agentic.tools.schemas import BaseToolConfig, ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_manager import ToolManager, ToolManagerConfig
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent, McpServer, McpTool
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model import LanguageModelService
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)


class _SharedServiceToolConfig(BaseToolConfig):
    pass


class _SharedServiceTool(Tool[_SharedServiceToolConfig]):
    """A tool that echoes the live assistant message id from ``ctx``."""

    name = "shared_service_tool"

    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name=self.name,
            description="test",
            parameters=dict,
        )

    async def run(
        self, tool_call: LanguageModelFunction, ctx: ToolExecutionContext
    ) -> ToolCallResponse:
        return ToolCallResponse(
            id=tool_call.id or "test_id",
            name=self.name,
            content=str(ctx.chat_service._assistant_message_id),
        )

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    def get_evaluation_checks_based_on_tool_response(self, tool_response):
        return []


@pytest.fixture
def chat_event() -> ChatEvent:
    event = Mock(spec=ChatEvent)
    event.company_id = "company-1"
    event.user_id = "user-1"
    event.payload = Mock()
    event.payload.chat_id = "chat-1"
    event.payload.assistant_message = Mock()
    event.payload.assistant_message.id = "assistant-msg-initial"
    event.payload.tool_choices = ["shared_service_tool"]
    event.payload.disabled_tools = []
    event.payload.mcp_servers = []
    return event


@pytest.fixture
def shared_chat_service(chat_event: ChatEvent) -> ChatService:
    return ChatService(chat_event)


@pytest.fixture
def shared_llm_service(chat_event: ChatEvent) -> LanguageModelService:
    return LanguageModelService.from_event(chat_event)


@pytest.fixture
def content_service(chat_event: ChatEvent) -> ContentService:
    return ContentService.from_event(chat_event)


@pytest.fixture
def mcp_manager() -> MCPManager:
    return MCPManager(mcp_servers=[])


@pytest.fixture
def a2a_manager() -> A2AManager:
    return A2AManager(
        logger=Mock(),
        tool_progress_reporter=Mock(spec=ToolProgressReporter),
        response_watcher=SubAgentResponseWatcher(),
    )


def _tool_manager_config() -> ToolManagerConfig:
    return ToolManagerConfig(
        tools=[
            ToolBuildConfig(
                name=_SharedServiceTool.name,
                configuration=_SharedServiceToolConfig(),
                display_name="Shared Service Tool",
                is_exclusive=False,
                is_enabled=True,
                icon=ToolIcon.BOOK,
                selection_policy=ToolSelectionPolicy.BY_USER,
            )
        ]
    )


@pytest.fixture
def registered_shared_service_tool():
    from unique_toolkit.agentic.tools.factory import ToolFactory

    ToolFactory.register_tool(_SharedServiceTool, _SharedServiceToolConfig)
    try:
        yield
    finally:
        ToolFactory.tool_map.pop(_SharedServiceTool.name, None)
        ToolFactory.tool_config_map.pop(_SharedServiceTool.name, None)


def test_tool_manager_execution_context_shares_injected_chat_service_instance(
    registered_shared_service_tool,
    chat_event: ChatEvent,
    shared_chat_service: ChatService,
    shared_llm_service: LanguageModelService,
    mcp_manager: MCPManager,
    a2a_manager: A2AManager,
) -> None:
    tool_manager = ToolManager(
        logger=Mock(),
        config=_tool_manager_config(),
        event=chat_event,
        tool_progress_reporter=Mock(spec=ToolProgressReporter),
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
        chat_service=shared_chat_service,
        language_model_service=shared_llm_service,
    )

    assert tool_manager.execution_context.chat_service is shared_chat_service
    assert tool_manager.get_tool_by_name(_SharedServiceTool.name) is not None


def test_tool_run_sees_live_chat_service_mutations_via_ctx(
    registered_shared_service_tool,
    chat_event: ChatEvent,
    shared_chat_service: ChatService,
    shared_llm_service: LanguageModelService,
    mcp_manager: MCPManager,
    a2a_manager: A2AManager,
) -> None:
    """Regression test for UN-19148: the assistant message id must never be stale.

    The tool is constructed (and the ToolManager/execution context built)
    before the assistant message id changes. Because ``ctx.chat_service`` is
    the exact same live object (not a snapshot), the tool must observe the
    updated id at ``run()`` time.
    """
    tool_manager = ToolManager(
        logger=Mock(),
        config=_tool_manager_config(),
        event=chat_event,
        tool_progress_reporter=Mock(spec=ToolProgressReporter),
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
        chat_service=shared_chat_service,
        language_model_service=shared_llm_service,
    )

    shared_chat_service._assistant_message_id = "assistant-msg-updated"

    tool_call = LanguageModelFunction(
        id="call-1", name=_SharedServiceTool.name, arguments={}
    )
    response = asyncio.run(tool_manager.execute_tool_call(tool_call))

    assert response.content == "assistant-msg-updated"


def test_mcp_tool_wrapper_uses_live_assistant_message_id_for_sdk_call(
    shared_chat_service: ChatService,
    shared_llm_service: LanguageModelService,
    content_service: ContentService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mcp_tool = McpTool(
        id="mcp-tool-id",
        name="mcp_tool",
        title="MCP Tool",
        description="desc",
        input_schema={"type": "object", "properties": {}},
        is_connected=True,
    )
    mcp_server = McpServer(
        id="server-1",
        name="test-server",
        description="test",
        tools=[mcp_tool],
        system_prompt="sys",
        user_prompt="user",
        is_connected=True,
    )
    wrapper = MCPToolWrapper(
        mcp_server=mcp_server,
        mcp_tool=mcp_server.tools[0],
        config=MCPToolConfig(
            server_id=mcp_server.id,
            server_name=mcp_server.name,
            server_system_prompt=mcp_server.system_prompt,
            server_user_prompt=mcp_server.user_prompt,
            mcp_source_id=mcp_server.id,
        ),
    )

    ctx = ToolExecutionContext.from_services(
        chat_service=shared_chat_service,
        language_model_service=shared_llm_service,
        content_service=content_service,
    )

    shared_chat_service._assistant_message_id = "assistant-msg-updated"
    captured: dict[str, str] = {}

    async def fake_call_tool_async(**kwargs):
        captured["messageId"] = kwargs["messageId"]
        return {}

    monkeypatch.setattr(
        "unique_toolkit.agentic.tools.mcp.tool_wrapper.unique_sdk.MCP.call_tool_async",
        fake_call_tool_async,
    )

    asyncio.run(wrapper._call_mcp_tool_via_sdk(ctx, {}))

    assert captured["messageId"] == "assistant-msg-updated"


def test_tool_manager_from_execution_context_shares_the_same_execution_context(
    registered_shared_service_tool,
    shared_chat_service: ChatService,
    shared_llm_service: LanguageModelService,
    content_service: ContentService,
    mcp_manager: MCPManager,
    a2a_manager: A2AManager,
) -> None:
    execution_context = ToolExecutionContext.from_services(
        chat_service=shared_chat_service,
        language_model_service=shared_llm_service,
        content_service=content_service,
    )

    tool_manager = ToolManager.from_execution_context(
        logger=Mock(),
        config=_tool_manager_config(),
        execution_context=execution_context,
        tool_choices=[_SharedServiceTool.name],
        disabled_tools=[],
        tool_progress_reporter=Mock(spec=ToolProgressReporter),
        mcp_manager=mcp_manager,
        a2a_manager=a2a_manager,
    )

    assert tool_manager.execution_context is execution_context

    execution_context.chat_service._assistant_message_id = "assistant-msg-updated"
    tool_call = LanguageModelFunction(
        id="call-1", name=_SharedServiceTool.name, arguments={}
    )
    response = asyncio.run(tool_manager.execute_tool_call(tool_call))

    assert response.content == "assistant-msg-updated"
