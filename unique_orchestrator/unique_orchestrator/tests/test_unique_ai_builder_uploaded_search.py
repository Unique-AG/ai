from unittest.mock import AsyncMock, MagicMock

import pytest
from unique_internal_search.uploaded_search.service import UploadedSearchTool
from unique_toolkit.agentic.tools.openai_builtin.base import OpenAIBuiltInToolName
from unique_toolkit.agentic.tools.tool_manager import ToolManagerConfig

from unique_orchestrator.config import CodeInterpreterExtendedConfig, UniqueAIConfig
from unique_orchestrator.unique_ai_builder import (
    _build_responses,
    _CommonComponents,
)


def _make_common_components(uploaded_documents):
    tool_manager_config = ToolManagerConfig(tools=[])
    return _CommonComponents(
        chat_service=MagicMock(),
        content_service=MagicMock(),
        llm_service=MagicMock(),
        uploaded_documents=uploaded_documents,
        thinking_manager=MagicMock(),
        reference_manager=MagicMock(),
        history_manager=MagicMock(),
        evaluation_manager=MagicMock(),
        postprocessor_manager=MagicMock(),
        message_step_logger=MagicMock(),
        response_watcher=MagicMock(),
        tool_progress_reporter=MagicMock(),
        tool_manager_config=tool_manager_config,
        mcp_manager=MagicMock(),
        a2a_manager=MagicMock(),
        mcp_servers=[],
    )


def _make_event(tool_choices):
    event = MagicMock()
    event.user_id = "user_1"
    event.company_id = "company_1"
    event.payload.assistant_id = "assistant_1"
    event.payload.chat_id = "chat_1"
    event.payload.tool_choices = tool_choices
    event.payload.mcp_servers = []
    return event


class _FakeResponsesApiToolManager:
    instances = []

    def __init__(self, *args, **kwargs):
        self.sub_agents = []
        self.forced_tools = []
        self.kwargs = kwargs
        self.__class__.instances.append(self)

    def add_forced_tool(self, tool_name: str) -> None:
        self.forced_tools.append(tool_name)


@pytest.mark.asyncio
async def test_build_responses_adds_and_forces_uploaded_search_without_tool_choices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = _make_event(tool_choices=[])
    uploaded_document = MagicMock(expired_at=None)
    common_components = _make_common_components([uploaded_document])
    config = UniqueAIConfig()
    logger = MagicMock()

    fake_client = MagicMock()
    fake_client.copy.return_value = fake_client

    _FakeResponsesApiToolManager.instances.clear()
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.get_async_openai_client",
        lambda: fake_client,
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.OpenAIBuiltInToolManager.build_manager",
        AsyncMock(return_value=MagicMock()),
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.ResponsesApiToolManager",
        _FakeResponsesApiToolManager,
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.build_loop_iteration_runner",
        lambda **kwargs: MagicMock(),
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.UniqueAI",
        lambda **kwargs: kwargs,
    )

    result = await _build_responses(
        event=event,
        logger=logger,
        config=config,
        common_components=common_components,
        debug_info_manager=MagicMock(),
    )

    uploaded_search_tools = [
        tool
        for tool in common_components.tool_manager_config.tools
        if tool.name == UploadedSearchTool.name
    ]

    assert len(uploaded_search_tools) == 1
    assert _FakeResponsesApiToolManager.instances[0].forced_tools == [
        UploadedSearchTool.name
    ]
    assert result["tool_manager"] is _FakeResponsesApiToolManager.instances[0]


@pytest.mark.asyncio
async def test_build_responses_appends_uploaded_search_to_existing_tool_choices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = _make_event(tool_choices=["InternalSearch"])
    uploaded_document = MagicMock(expired_at=None)
    common_components = _make_common_components([uploaded_document])
    config = UniqueAIConfig()

    fake_client = MagicMock()
    fake_client.copy.return_value = fake_client

    _FakeResponsesApiToolManager.instances.clear()
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.get_async_openai_client",
        lambda: fake_client,
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.OpenAIBuiltInToolManager.build_manager",
        AsyncMock(return_value=MagicMock()),
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.ResponsesApiToolManager",
        _FakeResponsesApiToolManager,
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.build_loop_iteration_runner",
        lambda **kwargs: MagicMock(),
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.UniqueAI",
        lambda **kwargs: kwargs,
    )

    await _build_responses(
        event=event,
        logger=MagicMock(),
        config=config,
        common_components=common_components,
        debug_info_manager=MagicMock(),
    )

    assert event.payload.tool_choices == [
        "InternalSearch",
        UploadedSearchTool.name,
    ]
    assert _FakeResponsesApiToolManager.instances[0].forced_tools == []


@pytest.mark.asyncio
async def test_build_responses_keeps_uploaded_search_when_code_interpreter_is_auto_added(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = _make_event(tool_choices=[])
    uploaded_document = MagicMock(expired_at=None)
    common_components = _make_common_components([uploaded_document])
    config = UniqueAIConfig()
    config.agent.experimental.responses_api_config.code_interpreter = (
        CodeInterpreterExtendedConfig()
    )
    logger = MagicMock()

    fake_client = MagicMock()
    fake_client.copy.return_value = fake_client

    _FakeResponsesApiToolManager.instances.clear()
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.get_async_openai_client",
        lambda: fake_client,
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.OpenAIBuiltInToolManager.build_manager",
        AsyncMock(return_value=MagicMock()),
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.ResponsesApiToolManager",
        _FakeResponsesApiToolManager,
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.build_loop_iteration_runner",
        lambda **kwargs: MagicMock(),
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.UniqueAI",
        lambda **kwargs: kwargs,
    )

    await _build_responses(
        event=event,
        logger=logger,
        config=config,
        common_components=common_components,
        debug_info_manager=MagicMock(),
    )

    tool_names = [tool.name for tool in common_components.tool_manager_config.tools]

    assert UploadedSearchTool.name in tool_names
    assert OpenAIBuiltInToolName.CODE_INTERPRETER in tool_names
    assert _FakeResponsesApiToolManager.instances[0].forced_tools == [
        UploadedSearchTool.name
    ]
