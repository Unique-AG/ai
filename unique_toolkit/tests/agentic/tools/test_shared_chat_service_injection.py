"""Regression tests for shared ChatService injection into tools (UN-19148)."""

from typing import overload
from unittest.mock import Mock

import pytest
from typing_extensions import deprecated

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.a2a import A2AManager
from unique_toolkit.agentic.tools.a2a.response_watcher import SubAgentResponseWatcher
from unique_toolkit.agentic.tools.config import (
    ToolBuildConfig,
    ToolIcon,
    ToolSelectionPolicy,
)
from unique_toolkit.agentic.tools.mcp.manager import MCPManager
from unique_toolkit.agentic.tools.mcp.models import MCPToolConfig
from unique_toolkit.agentic.tools.mcp.tool_wrapper import MCPToolWrapper
from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_manager import ToolManager, ToolManagerConfig
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent, McpServer, McpTool
from unique_toolkit.chat.service import ChatService
from unique_toolkit.language_model import LanguageModelService
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)


class _SharedServiceToolConfig(BaseToolConfig):
    pass


class _SharedServiceTool(Tool[_SharedServiceToolConfig]):
    name = "shared_service_tool"

    def __init__(self, configuration: _SharedServiceToolConfig, *args, **kwargs):
        super().__init__(configuration, *args, **kwargs)

    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name=self.name,
            description="test",
            parameters=dict,
        )

    async def run(self, tool_call: LanguageModelFunction):
        raise NotImplementedError

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    def get_evaluation_checks_based_on_tool_response(self, tool_response):
        return []


class _FixedInitToolConfig(BaseToolConfig):
    pass


class _FixedInitTool(Tool[_FixedInitToolConfig]):
    """Mirrors production tools (e.g. AskUser) with service-injection support."""

    name = "fixed_init_tool"

    @overload
    def __init__(
        self,
        config: _FixedInitToolConfig,
        *,
        chat_service: ChatService,
        language_model_service: LanguageModelService,
        tool_progress_reporter: ToolProgressReporter | None = ...,
    ) -> None: ...

    @overload
    @deprecated(
        "Passing event is deprecated. Inject chat_service and language_model_service."
    )
    def __init__(
        self,
        config: _FixedInitToolConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter | None = ...,
    ) -> None: ...

    def __init__(
        self,
        config: _FixedInitToolConfig,
        event: ChatEvent | None = None,
        tool_progress_reporter: ToolProgressReporter | None = None,
        *,
        chat_service: ChatService | None = None,
        language_model_service: LanguageModelService | None = None,
    ) -> None:
        if chat_service is not None and language_model_service is not None:
            super().__init__(
                config,
                tool_progress_reporter=tool_progress_reporter,
                chat_service=chat_service,
                language_model_service=language_model_service,
            )
        elif event is not None:
            super().__init__(config, event, tool_progress_reporter)
        else:
            raise ValueError(
                "_FixedInitTool requires event or injected chat_service and "
                "language_model_service"
            )

    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name=self.name,
            description="test",
            parameters=dict,
        )

    async def run(self, tool_call: LanguageModelFunction):
        raise NotImplementedError

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


def test_tool_init_with_injected_services_shares_chat_service_instance(
    chat_event: ChatEvent,
    shared_chat_service: ChatService,
    shared_llm_service: LanguageModelService,
) -> None:
    tool = _SharedServiceTool(
        _SharedServiceToolConfig(),
        chat_event,
        chat_service=shared_chat_service,
        language_model_service=shared_llm_service,
    )

    assert tool._chat_service is shared_chat_service
    assert tool.event is chat_event


def test_tool_manager_passes_shared_chat_service_to_internal_tools(
    chat_event: ChatEvent,
    shared_chat_service: ChatService,
    shared_llm_service: LanguageModelService,
) -> None:
    from unique_toolkit.agentic.tools.factory import ToolFactory

    ToolFactory.register_tool(_SharedServiceTool, _SharedServiceToolConfig)

    try:
        tool_manager = ToolManager(
            logger=Mock(),
            config=ToolManagerConfig(
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
            ),
            event=chat_event,
            tool_progress_reporter=Mock(spec=ToolProgressReporter),
            mcp_manager=MCPManager(
                mcp_servers=[],
                event=chat_event,
                tool_progress_reporter=Mock(spec=ToolProgressReporter),
                chat_service=shared_chat_service,
                language_model_service=shared_llm_service,
            ),
            a2a_manager=A2AManager(
                logger=Mock(),
                tool_progress_reporter=Mock(spec=ToolProgressReporter),
                response_watcher=SubAgentResponseWatcher(),
            ),
            chat_service=shared_chat_service,
            language_model_service=shared_llm_service,
        )

        internal_tool = tool_manager.get_tool_by_name(_SharedServiceTool.name)
        assert internal_tool is not None
        assert internal_tool._chat_service is shared_chat_service
    finally:
        ToolFactory.tool_map.pop(_SharedServiceTool.name, None)
        ToolFactory.tool_config_map.pop(_SharedServiceTool.name, None)


def test_tool_manager_injects_shared_services_into_custom_init_tools(
    chat_event: ChatEvent,
    shared_chat_service: ChatService,
    shared_llm_service: LanguageModelService,
) -> None:
    from unique_toolkit.agentic.tools.factory import ToolFactory

    ToolFactory.register_tool(_FixedInitTool, _FixedInitToolConfig)
    chat_event.payload.tool_choices = [_FixedInitTool.name]

    try:
        tool_manager = ToolManager(
            logger=Mock(),
            config=ToolManagerConfig(
                tools=[
                    ToolBuildConfig(
                        name=_FixedInitTool.name,
                        configuration=_FixedInitToolConfig(),
                        display_name="Fixed Init Tool",
                        is_exclusive=False,
                        is_enabled=True,
                        icon=ToolIcon.BOOK,
                        selection_policy=ToolSelectionPolicy.BY_USER,
                    )
                ]
            ),
            event=chat_event,
            tool_progress_reporter=Mock(spec=ToolProgressReporter),
            mcp_manager=MCPManager(
                mcp_servers=[],
                event=chat_event,
                tool_progress_reporter=Mock(spec=ToolProgressReporter),
            ),
            a2a_manager=A2AManager(
                logger=Mock(),
                tool_progress_reporter=Mock(spec=ToolProgressReporter),
                response_watcher=SubAgentResponseWatcher(),
            ),
            chat_service=shared_chat_service,
            language_model_service=shared_llm_service,
        )

        fixed_init_tool = tool_manager.get_tool_by_name(_FixedInitTool.name)
        assert fixed_init_tool is not None
        assert fixed_init_tool._chat_service is shared_chat_service
    finally:
        ToolFactory.tool_map.pop(_FixedInitTool.name, None)
        ToolFactory.tool_config_map.pop(_FixedInitTool.name, None)


def test_mcp_tool_wrapper_uses_live_assistant_message_id_for_sdk_call(
    chat_event: ChatEvent,
    shared_chat_service: ChatService,
    shared_llm_service: LanguageModelService,
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
        chat_service=shared_chat_service,
        language_model_service=shared_llm_service,
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

    import asyncio

    asyncio.run(wrapper._call_mcp_tool_via_sdk({}))

    assert captured["messageId"] == "assistant-msg-updated"
