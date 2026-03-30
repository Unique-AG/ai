from datetime import datetime
from logging import getLogger
from unittest.mock import AsyncMock, Mock

import pytest
from pytest_mock import MockerFixture
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.content.schemas import ContentInfo
from unique_toolkit.language_model.schemas import LanguageModelFunction

from unique_retrieve_search_scope.config import RetrieveSearchScopeConfig
from unique_retrieve_search_scope.service import RetrieveSearchScopeTool

_KB_SERVICE_PATH = (
    "unique_retrieve_search_scope.service.UniqueServiceFactory.knowledge_base_service"
)
_SETTINGS_PATH = "unique_retrieve_search_scope.service.UniqueSettings.from_chat_event"
_MODEL_INFO_PATH = "unique_retrieve_search_scope.service.LanguageModelInfo.from_name"


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
    payload.configuration = {}
    event.payload = payload
    return event


@pytest.fixture
def tool(mock_chat_event: ChatEvent, mocker: MockerFixture) -> RetrieveSearchScopeTool:
    config = RetrieveSearchScopeConfig()

    def setup_tool(self, configuration, event, *args, **kwargs):
        setattr(self, "_event", event)
        setattr(self, "logger", getLogger("test"))
        setattr(self, "_message_step_logger", None)
        setattr(self, "_tool_progress_reporter", None)
        setattr(self, "config", configuration)
        setattr(self, "debug_info", {})
        settings_mock = Mock()
        settings_mock.display_name = ""
        setattr(self, "settings", settings_mock)

    mocker.patch("unique_retrieve_search_scope.service.Tool.__init__", setup_tool)
    return RetrieveSearchScopeTool(config, mock_chat_event)


@pytest.fixture
def mock_tool_call() -> LanguageModelFunction:
    tool_call: LanguageModelFunction = Mock(spec=LanguageModelFunction)
    tool_call.id = "call_123"
    tool_call.arguments = {}
    return tool_call


def _stub_kb(
    mocker: MockerFixture,
    content_infos=None,
    side_effect=None,
    space_metadata_filter=None,
):
    mocker.patch(_SETTINGS_PATH)
    mock_kb = Mock()
    mock_kb._metadata_filter = space_metadata_filter
    if side_effect:
        mock_kb.get_content_infos_async = AsyncMock(side_effect=side_effect)
    else:
        mock_kb.get_content_infos_async = AsyncMock(
            return_value=content_infos if content_infos is not None else []
        )
    mocker.patch(_KB_SERVICE_PATH, return_value=mock_kb)
    return mock_kb


@pytest.mark.unit
class TestRetrieveSearchScopeToolRun:
    async def test_returns_empty_message_when_no_files(
        self,
        tool: RetrieveSearchScopeTool,
        mock_tool_call: LanguageModelFunction,
        mocker: MockerFixture,
    ):
        _stub_kb(mocker, [])
        response = await tool.run(mock_tool_call)

        assert response.successful
        assert "No files found" in response.content

    async def test_lists_duplicate_names_individually_with_content_ids(
        self,
        tool: RetrieveSearchScopeTool,
        mock_tool_call: LanguageModelFunction,
        mocker: MockerFixture,
    ):
        content_infos = [
            _make_content_info("report.pdf", id="id_1"),
            _make_content_info("report.pdf", id="id_2"),
            _make_content_info("other.pdf"),
        ]
        _stub_kb(mocker, content_infos)
        response = await tool.run(mock_tool_call)

        assert "3 of 3 files" in response.content
        assert "report.pdf (id_1)" in response.content
        assert "report.pdf (id_2)" in response.content
        assert "other.pdf (id_other.pdf)" in response.content

    async def test_passes_metadata_filter(
        self,
        tool: RetrieveSearchScopeTool,
        mock_tool_call: LanguageModelFunction,
        mocker: MockerFixture,
    ):
        mock_tool_call.arguments = {"metadata_filter": {"env": "prod"}}
        mock_kb = _stub_kb(mocker, [])
        await tool.run(mock_tool_call)

        mock_kb.get_content_infos_async.assert_called_once_with(
            metadata_filter={"env": "prod"},
        )

    async def test_handles_no_arguments(
        self,
        tool: RetrieveSearchScopeTool,
        mock_tool_call: LanguageModelFunction,
        mocker: MockerFixture,
    ):
        mock_tool_call.arguments = None
        mock_kb = _stub_kb(mocker, [])
        response = await tool.run(mock_tool_call)

        mock_kb.get_content_infos_async.assert_called_once_with(
            metadata_filter=None,
        )
        assert response.successful

    async def test_uses_space_filter_when_no_agent_filter(
        self,
        tool: RetrieveSearchScopeTool,
        mock_tool_call: LanguageModelFunction,
        mocker: MockerFixture,
    ):
        mock_tool_call.arguments = {}
        space_filter = {
            "operator": "equals",
            "value": "finance",
            "path": ["department"],
        }
        mock_kb = _stub_kb(mocker, [], space_metadata_filter=space_filter)
        await tool.run(mock_tool_call)

        mock_kb.get_content_infos_async.assert_called_once_with(
            metadata_filter=space_filter,
        )

    async def test_combines_space_and_agent_filters_with_and(
        self,
        tool: RetrieveSearchScopeTool,
        mock_tool_call: LanguageModelFunction,
        mocker: MockerFixture,
    ):
        agent_filter = {"operator": "equals", "value": "prod", "path": ["env"]}
        mock_tool_call.arguments = {"metadata_filter": agent_filter}
        space_filter = {
            "operator": "equals",
            "value": "finance",
            "path": ["department"],
        }
        mock_kb = _stub_kb(mocker, [], space_metadata_filter=space_filter)
        await tool.run(mock_tool_call)

        mock_kb.get_content_infos_async.assert_called_once_with(
            metadata_filter={"and": [space_filter, agent_filter]},
        )

    async def test_uses_only_agent_filter_when_no_space_filter(
        self,
        tool: RetrieveSearchScopeTool,
        mock_tool_call: LanguageModelFunction,
        mocker: MockerFixture,
    ):
        agent_filter = {"operator": "equals", "value": "prod", "path": ["env"]}
        mock_tool_call.arguments = {"metadata_filter": agent_filter}
        mock_kb = _stub_kb(mocker, [])
        await tool.run(mock_tool_call)

        mock_kb.get_content_infos_async.assert_called_once_with(
            metadata_filter=agent_filter,
        )

    async def test_returns_error_on_kb_failure(
        self,
        tool: RetrieveSearchScopeTool,
        mock_tool_call: LanguageModelFunction,
        mocker: MockerFixture,
    ):
        mocker.patch(_SETTINGS_PATH, side_effect=RuntimeError("connection failed"))
        response = await tool.run(mock_tool_call)

        assert not response.successful
        assert "Failed to retrieve" in response.error_message


@pytest.mark.unit
class TestContentIdForOpenableFiles:
    @pytest.mark.parametrize(
        "filename, mime_type",
        [
            ("doc.pdf", "application/pdf"),
            (
                "doc.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            ("doc.doc", "application/msword"),
            (
                "slides.pptx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ),
            ("slides.ppt", "application/vnd.ms-powerpoint"),
        ],
    )
    async def test_openable_mime_types_include_content_id(
        self,
        tool: RetrieveSearchScopeTool,
        mock_tool_call: LanguageModelFunction,
        mocker: MockerFixture,
        filename: str,
        mime_type: str,
    ):
        content_infos = [
            _make_content_info(filename, mime_type=mime_type, id="cont_123")
        ]
        _stub_kb(mocker, content_infos)
        response = await tool.run(mock_tool_call)
        assert f"{filename} (cont_123)" in response.content

    async def test_openable_file_without_id_does_not_append_content_id(
        self,
        tool: RetrieveSearchScopeTool,
        mock_tool_call: LanguageModelFunction,
        mocker: MockerFixture,
    ):
        content_infos = [
            _make_content_info("doc.pdf", mime_type="application/pdf", id="")
        ]
        _stub_kb(mocker, content_infos)
        response = await tool.run(mock_tool_call)
        file_section = response.content.split("\n\n", 1)[1]
        assert file_section.strip() == "doc.pdf"

    @pytest.mark.parametrize(
        "filename, mime_type",
        [
            (
                "data.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            ("notes.txt", "text/plain"),
        ],
    )
    async def test_non_openable_mime_types_exclude_content_id(
        self,
        tool: RetrieveSearchScopeTool,
        mock_tool_call: LanguageModelFunction,
        mocker: MockerFixture,
        filename: str,
        mime_type: str,
    ):
        content_infos = [
            _make_content_info(
                filename, mime_type=mime_type, id="cont_should_not_appear"
            )
        ]
        _stub_kb(mocker, content_infos)
        response = await tool.run(mock_tool_call)
        file_section = response.content.split("\n\n", 1)[1]
        assert file_section.strip() == filename


@pytest.mark.unit
class TestTokenTruncation:
    async def test_truncates_when_exceeding_token_budget(
        self,
        tool: RetrieveSearchScopeTool,
        mock_tool_call: LanguageModelFunction,
        mocker: MockerFixture,
    ):
        tool._event.payload.configuration = {"space": {"languageModel": "any-model"}}
        tool.config.context_window_fraction_for_file_list = 0.5

        model_info = Mock()
        model_info.token_limits.token_limit_input = 20
        mocker.patch(_MODEL_INFO_PATH, return_value=model_info)

        content_infos = [
            _make_content_info(f"file_{i}.txt", mime_type="text/plain")
            for i in range(100)
        ]
        _stub_kb(mocker, content_infos)
        response = await tool.run(mock_tool_call)

        assert response.successful
        assert "omitted due to token budget" in response.content
        assert "100 files in search scope" in response.content

    async def test_returns_all_files_when_no_model_name(
        self,
        tool: RetrieveSearchScopeTool,
        mock_tool_call: LanguageModelFunction,
        mocker: MockerFixture,
    ):
        tool._event.payload.configuration = {}

        content_infos = [
            _make_content_info(f"file_{i}.txt", mime_type="text/plain")
            for i in range(50)
        ]
        _stub_kb(mocker, content_infos)
        response = await tool.run(mock_tool_call)

        assert response.successful
        assert "50 of 50 files" in response.content
        assert "omitted" not in response.content

    async def test_no_truncation_when_within_budget(
        self,
        tool: RetrieveSearchScopeTool,
        mock_tool_call: LanguageModelFunction,
        mocker: MockerFixture,
    ):
        tool._event.payload.configuration = {"space": {"languageModel": "any-model"}}
        tool.config.context_window_fraction_for_file_list = 1.0

        model_info = Mock()
        model_info.token_limits.token_limit_input = 100_000
        mocker.patch(_MODEL_INFO_PATH, return_value=model_info)

        content_infos = [
            _make_content_info("small.txt", mime_type="text/plain"),
        ]
        _stub_kb(mocker, content_infos)
        response = await tool.run(mock_tool_call)

        assert response.successful
        assert "1 of 1 files" in response.content
        assert "omitted" not in response.content


@pytest.mark.unit
class TestHistoryGuard:
    async def test_short_circuits_when_prior_call_in_history(
        self, tool: RetrieveSearchScopeTool, mock_tool_call: LanguageModelFunction
    ):
        prior_tc = Mock()
        prior_tc.function.name = "RetrieveSearchScope"
        prior_msg = Mock()
        prior_msg.role.value = "assistant"
        prior_msg.tool_calls = [prior_tc]

        mock_chat_service = Mock()
        mock_chat_service.get_full_history_async = AsyncMock(return_value=[prior_msg])
        tool._chat_service = mock_chat_service

        response = await tool.run(mock_tool_call)

        assert response.successful
        assert "already been called" in response.content

    async def test_proceeds_when_no_prior_call_in_history(
        self,
        tool: RetrieveSearchScopeTool,
        mock_tool_call: LanguageModelFunction,
        mocker: MockerFixture,
    ):
        user_msg = Mock()
        user_msg.role.value = "user"
        user_msg.tool_calls = None

        mock_chat_service = Mock()
        mock_chat_service.get_full_history_async = AsyncMock(return_value=[user_msg])
        tool._chat_service = mock_chat_service

        _stub_kb(mocker, [])
        response = await tool.run(mock_tool_call)

        assert response.successful
        assert "No files found" in response.content

    async def test_proceeds_when_history_check_fails(
        self,
        tool: RetrieveSearchScopeTool,
        mock_tool_call: LanguageModelFunction,
        mocker: MockerFixture,
    ):
        mock_chat_service = Mock()
        mock_chat_service.get_full_history_async = AsyncMock(
            side_effect=RuntimeError("service unavailable")
        )
        tool._chat_service = mock_chat_service

        _stub_kb(mocker, [])
        response = await tool.run(mock_tool_call)

        assert response.successful
        assert "No files found" in response.content


@pytest.mark.unit
class TestDisplayName:
    def test_returns_default_when_settings_display_name_empty(
        self, tool: RetrieveSearchScopeTool
    ):
        tool.settings.display_name = ""
        assert tool.display_name() == "Retrieve Search Scope"

    def test_returns_custom_display_name_from_settings(
        self, tool: RetrieveSearchScopeTool
    ):
        tool.settings.display_name = "KB File List"
        assert tool.display_name() == "KB File List"

    def test_default_display_name_class_attribute(self):
        assert RetrieveSearchScopeTool.default_display_name == "Retrieve Search Scope"


@pytest.mark.unit
class TestRetrieveSearchScopeToolDescription:
    def test_tool_description_has_metadata_filter_param(
        self, tool: RetrieveSearchScopeTool
    ):
        desc = tool.tool_description()
        assert not isinstance(desc.parameters, dict)
        schema = desc.parameters.model_json_schema()
        assert "metadata_filter" in schema["properties"]
