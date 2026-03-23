from datetime import datetime
from logging import getLogger
from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.content.schemas import ContentInfo
from unique_toolkit.language_model.schemas import LanguageModelFunction

from unique_retrieve_search_scope.config import RetrieveSearchScopeConfig
from unique_retrieve_search_scope.service import RetrieveSearchScopeTool

_KB_SERVICE_PATCH = (
    "unique_retrieve_search_scope.service.UniqueServiceFactory.knowledge_base_service"
)
_SETTINGS_PATCH = (
    "unique_retrieve_search_scope.service.UniqueSettings.from_chat_event"
)


def _make_content_info(key: str, **kwargs) -> ContentInfo:
    defaults = {
        "id": f"id_{key}",
        "object": "content_info",
        "key": key,
        "byte_size": 1024,
        "mime_type": "application/pdf",
        "owner_id": "owner_1",
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 1, 1),
    }
    defaults.update(kwargs)
    return ContentInfo(**defaults)


@pytest.fixture
def mock_chat_event() -> ChatEvent:
    event: ChatEvent = Mock(spec=ChatEvent)
    event.company_id = "company_123"
    event.user_id = "user_123"
    payload = Mock()
    payload.chat_id = "chat_123"
    event.payload = payload
    return event


@pytest.fixture
def tool(mock_chat_event: ChatEvent) -> RetrieveSearchScopeTool:
    config = RetrieveSearchScopeConfig()

    def setup_tool(self, configuration, event, *args, **kwargs):
        setattr(self, "_event", event)
        setattr(self, "logger", getLogger("test"))
        setattr(self, "_message_step_logger", None)
        setattr(self, "_tool_progress_reporter", None)
        setattr(self, "config", configuration)
        setattr(self, "debug_info", {})

    with patch(
        "unique_retrieve_search_scope.service.Tool.__init__", setup_tool
    ):
        return RetrieveSearchScopeTool(config, mock_chat_event)


@pytest.fixture
def mock_tool_call() -> LanguageModelFunction:
    tool_call: LanguageModelFunction = Mock(spec=LanguageModelFunction)
    tool_call.id = "call_123"
    tool_call.arguments = {}
    return tool_call


def _patch_kb(content_infos=None, side_effect=None, space_metadata_filter=None):
    mock_kb = Mock()
    mock_kb._metadata_filter = space_metadata_filter
    if side_effect:
        mock_kb.get_content_infos_async = AsyncMock(side_effect=side_effect)
    else:
        mock_kb.get_content_infos_async = AsyncMock(
            return_value=content_infos if content_infos is not None else []
        )
    return patch(_SETTINGS_PATCH), patch(_KB_SERVICE_PATCH, return_value=mock_kb), mock_kb


@pytest.mark.unit
class TestRetrieveSearchScopeToolRun:
    async def test_returns_sorted_file_names(
        self, tool: RetrieveSearchScopeTool, mock_tool_call: LanguageModelFunction
    ):
        content_infos = [
            _make_content_info("zebra.pdf"),
            _make_content_info("alpha.docx"),
            _make_content_info("middle.txt"),
        ]

        settings_patch, kb_patch, _ = _patch_kb(content_infos)
        with settings_patch, kb_patch:
            response = await tool.run(mock_tool_call)

        assert isinstance(response, ToolCallResponse)
        assert response.successful
        assert "3 files" in response.content
        lines = response.content.strip().split("\n")
        file_lines = [l for l in lines if l and not l.startswith("Found")]
        assert file_lines == ["alpha.docx", "middle.txt", "zebra.pdf"]

    async def test_returns_empty_message_when_no_files(
        self, tool: RetrieveSearchScopeTool, mock_tool_call: LanguageModelFunction
    ):
        settings_patch, kb_patch, _ = _patch_kb([])
        with settings_patch, kb_patch:
            response = await tool.run(mock_tool_call)

        assert response.successful
        assert "No files found" in response.content

    async def test_deduplicates_file_names(
        self, tool: RetrieveSearchScopeTool, mock_tool_call: LanguageModelFunction
    ):
        content_infos = [
            _make_content_info("report.pdf", id="id_1"),
            _make_content_info("report.pdf", id="id_2"),
            _make_content_info("other.pdf"),
        ]

        settings_patch, kb_patch, _ = _patch_kb(content_infos)
        with settings_patch, kb_patch:
            response = await tool.run(mock_tool_call)

        assert "2 files" in response.content

    async def test_passes_metadata_filter(
        self, tool: RetrieveSearchScopeTool, mock_tool_call: LanguageModelFunction
    ):
        mock_tool_call.arguments = {"metadata_filter": {"env": "prod"}}

        settings_patch, kb_patch, mock_kb = _patch_kb([])
        with settings_patch, kb_patch:
            await tool.run(mock_tool_call)

            mock_kb.get_content_infos_async.assert_called_once_with(
                metadata_filter={"env": "prod"},
            )

    async def test_handles_no_arguments(
        self, tool: RetrieveSearchScopeTool, mock_tool_call: LanguageModelFunction
    ):
        mock_tool_call.arguments = None

        settings_patch, kb_patch, mock_kb = _patch_kb([])
        with settings_patch, kb_patch:
            response = await tool.run(mock_tool_call)

            mock_kb.get_content_infos_async.assert_called_once_with(
                metadata_filter=None,
            )
            assert response.successful

    async def test_uses_space_filter_when_no_agent_filter(
        self, tool: RetrieveSearchScopeTool, mock_tool_call: LanguageModelFunction
    ):
        mock_tool_call.arguments = {}
        space_filter = {"operator": "equals", "value": "finance", "path": ["department"]}

        settings_patch, kb_patch, mock_kb = _patch_kb(
            [], space_metadata_filter=space_filter
        )
        with settings_patch, kb_patch:
            await tool.run(mock_tool_call)

            mock_kb.get_content_infos_async.assert_called_once_with(
                metadata_filter=space_filter,
            )

    async def test_combines_space_and_agent_filters_with_and(
        self, tool: RetrieveSearchScopeTool, mock_tool_call: LanguageModelFunction
    ):
        agent_filter = {"operator": "equals", "value": "prod", "path": ["env"]}
        mock_tool_call.arguments = {"metadata_filter": agent_filter}
        space_filter = {"operator": "equals", "value": "finance", "path": ["department"]}

        settings_patch, kb_patch, mock_kb = _patch_kb(
            [], space_metadata_filter=space_filter
        )
        with settings_patch, kb_patch:
            await tool.run(mock_tool_call)

            mock_kb.get_content_infos_async.assert_called_once_with(
                metadata_filter={"and": [space_filter, agent_filter]},
            )

    async def test_uses_only_agent_filter_when_no_space_filter(
        self, tool: RetrieveSearchScopeTool, mock_tool_call: LanguageModelFunction
    ):
        agent_filter = {"operator": "equals", "value": "prod", "path": ["env"]}
        mock_tool_call.arguments = {"metadata_filter": agent_filter}

        settings_patch, kb_patch, mock_kb = _patch_kb([])
        with settings_patch, kb_patch:
            await tool.run(mock_tool_call)

            mock_kb.get_content_infos_async.assert_called_once_with(
                metadata_filter=agent_filter,
            )

    async def test_returns_error_on_kb_failure(
        self, tool: RetrieveSearchScopeTool, mock_tool_call: LanguageModelFunction
    ):
        with patch(_SETTINGS_PATCH, side_effect=RuntimeError("connection failed")):
            response = await tool.run(mock_tool_call)

        assert not response.successful
        assert "Failed to retrieve" in response.error_message


@pytest.mark.unit
class TestRetrieveSearchScopeToolDescription:
    def test_tool_name(self, tool: RetrieveSearchScopeTool):
        assert tool.name == "RetrieveSearchScope"

    def test_tool_description_has_metadata_filter_param(
        self, tool: RetrieveSearchScopeTool
    ):
        desc = tool.tool_description()
        assert not isinstance(desc.parameters, dict)
        schema = desc.parameters.model_json_schema()
        assert "metadata_filter" in schema["properties"]

    def test_evaluation_check_list_is_empty(self, tool: RetrieveSearchScopeTool):
        assert tool.evaluation_check_list() == []
