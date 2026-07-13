from unittest.mock import AsyncMock, MagicMock

import pytest
from unique_internal_search.uploaded_search.service import UploadedSearchTool
from unique_toolkit.agentic.tools.experimental.open_file_tool import OpenFileTool
from unique_toolkit.agentic.tools.openai_builtin.base import OpenAIBuiltInToolName
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.config import (
    CodeInterpreterExtendedConfig,
)
from unique_toolkit.agentic.tools.tool import ToolBuildConfig
from unique_toolkit.agentic.tools.tool_manager import ToolManagerConfig
from unique_toolkit.content.schemas import Content
from unique_user_memory.user_memory import UserMemoryState

from unique_orchestrator._builders.history_manager import (
    build_history_manager,
    serialize_uploaded_file_for_history,
)
from unique_orchestrator._builders.open_file_setup import configure_file_payload
from unique_orchestrator.config import UniqueAIConfig, UploadedSearchToolConfig
from unique_orchestrator.unique_ai_builder import (
    _build_common,
    _build_responses,
    _CommonComponents,
    _configure_uploaded_search_tool,
)


def _make_common_components(uploaded_documents):
    tool_manager_config = ToolManagerConfig(tools=[])
    return _CommonComponents(
        chat_service=MagicMock(),
        content_service=MagicMock(),
        llm_service=MagicMock(),
        uploaded_documents=uploaded_documents,
        uploaded_images=[],
        thinking_manager=MagicMock(),
        reference_manager=MagicMock(),
        evaluation_manager=MagicMock(),
        postprocessor_manager=MagicMock(),
        message_step_logger=MagicMock(),
        response_watcher=MagicMock(),
        tool_progress_reporter=MagicMock(),
        tool_manager_config=tool_manager_config,
        mcp_manager=MagicMock(),
        a2a_manager=MagicMock(),
        mcp_servers=[],
        user_memory_text="",
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


def _patch_build_common_user_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[MagicMock, AsyncMock]:
    event = _make_event(tool_choices=[])
    event.payload.additional_parameters = None
    event.payload.mcp_servers = []

    chat_service = MagicMock()
    chat_service.download_chat_images_and_documents_async = AsyncMock(
        return_value=([], [])
    )
    content_service = MagicMock()

    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.ChatService",
        MagicMock(return_value=chat_service),
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.ContentService.from_event",
        MagicMock(return_value=content_service),
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.LanguageModelService.from_event",
        MagicMock(return_value=MagicMock()),
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.ToolProgressReporter",
        MagicMock(return_value=MagicMock()),
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.ThinkingManager",
        MagicMock(return_value=MagicMock()),
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.EvaluationManager",
        MagicMock(return_value=MagicMock()),
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.MCPManager",
        MagicMock(return_value=MagicMock()),
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.A2AManager",
        MagicMock(return_value=MagicMock()),
    )
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.MessageStepLogger",
        MagicMock(return_value=MagicMock()),
    )
    memory_state = UserMemoryState(scope_id="scope_1", text="remembered")
    load_user_memory = AsyncMock(return_value=memory_state)
    monkeypatch.setattr(
        "unique_orchestrator.unique_ai_builder.load_user_memory",
        load_user_memory,
    )

    return event, load_user_memory


@pytest.mark.asyncio
async def test_build_common_skips_user_memory_when_space_disallows_user_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event, load_user_memory = _patch_build_common_user_memory(monkeypatch)

    config = UniqueAIConfig()

    common_components = await _build_common(
        event=event,
        logger=MagicMock(),
        config=config,
    )

    load_user_memory.assert_not_awaited()
    assert common_components.user_memory_text == ""
    postprocessor_names = [
        postprocessor.name
        for postprocessor in common_components.postprocessor_manager.get_postprocessors(
            "ignored"
        )
    ]
    assert "UserMemoryPostprocessor" not in postprocessor_names


@pytest.mark.asyncio
async def test_build_common_registers_user_memory_when_space_allow_user_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event, load_user_memory = _patch_build_common_user_memory(monkeypatch)

    config = UniqueAIConfig(space={"allowUserMemory": True})
    common_components = await _build_common(
        event=event,
        logger=MagicMock(),
        config=config,
    )

    load_user_memory.assert_awaited_once()
    assert common_components.user_memory_text == "remembered"
    postprocessor_names = [
        postprocessor.name
        for postprocessor in common_components.postprocessor_manager.get_postprocessors(
            "ignored"
        )
    ]
    assert "UserMemoryPostprocessor" in postprocessor_names


class TestSerializeUploadedFileForHistory:
    def test_describes_all_available_file_operations(self) -> None:
        content = Content(id="cont_1", key="report.pdf")

        result = serialize_uploaded_file_for_history(
            content,
            uploaded_search_available=True,
            code_interpreter_available=True,
        )

        assert result == (
            "User uploaded file: report.pdf (cont_1)\n"
            "- Searchable using UploadedSearchTool\n"
            "- Available for processing in the code execution container"
        )

    def test_omits_search_for_non_ingested_file(self) -> None:
        content = Content(
            id="cont_1",
            key="report.pdf",
            applied_ingestion_config={"uniqueIngestionMode": "SKIP_INGESTION"},
        )

        result = serialize_uploaded_file_for_history(
            content,
            uploaded_search_available=True,
            code_interpreter_available=False,
        )

        assert result == "User uploaded file: report.pdf (cont_1)"

    def test_excludes_code_interpreter_generated_file(self) -> None:
        content = Content(
            id="cont_1",
            key="generated.csv",
            metadata={
                "codeExecutionArtifactMetadata": {
                    "container_id": "container_1",
                    "file_id": "file_1",
                    "filepath": "/mnt/data/generated.csv",
                }
            },
        )

        result = serialize_uploaded_file_for_history(
            content,
            uploaded_search_available=True,
            code_interpreter_available=True,
        )

        assert result is None


class _FakeResponsesApiToolManager:
    instances = []

    def __init__(self, *args, **kwargs):
        self.sub_agents = []
        self.forced_tools = []
        self.kwargs = kwargs
        self.__class__.instances.append(self)

    def add_forced_tool(self, tool_name: str) -> None:
        self.forced_tools.append(tool_name)

    def add_tool(self, tool: object) -> None:
        return None

    def get_tool_by_name(self, tool_name: str):
        return next(
            (
                tool
                for tool in self.kwargs["config"].tools
                if tool.is_enabled and tool.name == tool_name
            ),
            None,
        )


def test_configure_file_payload_registers_open_file_tool() -> None:
    config = UniqueAIConfig()
    config.agent.experimental.open_file_tool_config.send_files_in_payload = True
    event = _make_event(tool_choices=[])
    tool_manager = MagicMock()

    registry = configure_file_payload(config, event, tool_manager)

    registered_tool = tool_manager.add_tool.call_args.args[0]
    assert isinstance(registered_tool, OpenFileTool)
    assert registry == []


@pytest.mark.asyncio
async def test_build_responses_adds_and_forces_uploaded_search_without_tool_choices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = _make_event(tool_choices=[])
    uploaded_document = MagicMock()
    uploaded_document.is_expired.return_value = False
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
    uploaded_document = MagicMock()
    uploaded_document.is_expired.return_value = False
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
    uploaded_document = MagicMock()
    uploaded_document.is_expired.return_value = False
    common_components = _make_common_components([uploaded_document])
    config = UniqueAIConfig()
    config.space.tools.append(
        ToolBuildConfig(
            name=OpenAIBuiltInToolName.CODE_INTERPRETER,
            configuration=CodeInterpreterExtendedConfig(),
        )
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

    tool_manager_tool_names = [
        tool.name for tool in common_components.tool_manager_config.tools
    ]
    space_tool_names = [tool.name for tool in config.space.tools]

    assert UploadedSearchTool.name in tool_manager_tool_names
    assert OpenAIBuiltInToolName.CODE_INTERPRETER in space_tool_names
    assert _FakeResponsesApiToolManager.instances[0].forced_tools == [
        UploadedSearchTool.name
    ]


def test_build_history_manager_uses_final_tool_availability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = _make_event(tool_choices=[])
    reference_manager = MagicMock()
    logger = MagicMock()
    tool_manager = MagicMock()
    tool_manager.get_tool_by_name.return_value = object()
    config = UniqueAIConfig()
    config.agent.input_token_distribution.enable_tool_call_persistence = True
    config.agent.input_token_distribution.serialize_uploaded_files_in_user_message = (
        True
    )
    language_model = config.space.language_model

    captured: dict[str, object] = {}

    class _FakeHistoryManager:
        def __init__(
            self,
            logger_arg,
            event_arg,
            config_arg,
            language_model_arg,
            reference_manager_arg,
            *,
            file_content_serializer,
        ):
            captured["logger"] = logger_arg
            captured["event"] = event_arg
            captured["config"] = config_arg
            captured["language_model"] = language_model_arg
            captured["reference_manager"] = reference_manager_arg
            captured["file_content_serializer"] = file_content_serializer

    monkeypatch.setattr(
        "unique_orchestrator._builders.history_manager.HistoryManager",
        _FakeHistoryManager,
    )

    history_manager = build_history_manager(
        event=event,
        logger=logger,
        config=config,
        reference_manager=reference_manager,
        tool_manager=tool_manager,
    )

    assert isinstance(history_manager, _FakeHistoryManager)
    assert captured["logger"] is logger
    assert captured["event"] is event
    assert captured["language_model"] is language_model
    assert captured["reference_manager"] is reference_manager
    assert captured["config"].language_model is language_model
    assert captured["config"].enable_tool_call_persistence is True
    file_content_serializer = captured["file_content_serializer"]
    assert callable(file_content_serializer)
    assert file_content_serializer(Content(id="cont_1", key="report.pdf")) == (
        "User uploaded file: report.pdf (cont_1)\n"
        "- Searchable using UploadedSearchTool\n"
        "- Available for processing in the code execution container"
    )


class TestConfigureUploadedSearchToolIngestionFilter:
    def _make_event(self, tool_choices=None):
        event = MagicMock()
        event.payload.tool_choices = tool_choices or []
        return event

    def _make_doc(self, applied_ingestion_config, mime_type=None):
        return Content(
            expired_at=None,
            applied_ingestion_config=applied_ingestion_config,
            mime_type=mime_type,
        )

    def _run(self, docs, tool_choices=None, config=None):
        common_components = _make_common_components(docs)
        event = self._make_event(tool_choices)
        _configure_uploaded_search_tool(
            event=event,
            logger=MagicMock(),
            common_components=common_components,
            config=config or UploadedSearchToolConfig(),
        )
        return common_components

    def test_none_applied_ingestion_config_is_included(self):
        doc = self._make_doc(None)
        common = self._run([doc])
        tool_names = [t.name for t in common.tool_manager_config.tools]
        assert UploadedSearchTool.name in tool_names

    def test_standard_ingestion_mode_is_included(self):
        doc = self._make_doc({"uniqueIngestionMode": "INGESTION"})
        common = self._run([doc])
        tool_names = [t.name for t in common.tool_manager_config.tools]
        assert UploadedSearchTool.name in tool_names

    def test_skip_ingestion_mode_is_excluded(self):
        doc = self._make_doc({"uniqueIngestionMode": "SKIP_INGESTION"})
        common = self._run([doc])
        tool_names = [t.name for t in common.tool_manager_config.tools]
        assert UploadedSearchTool.name not in tool_names

    def test_skip_excel_ingestion_mode_is_excluded(self):
        doc = self._make_doc(
            {"uniqueIngestionMode": "SKIP_EXCEL_INGESTION"},
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        common = self._run([doc])
        tool_names = [t.name for t in common.tool_manager_config.tools]
        assert UploadedSearchTool.name not in tool_names

    def test_skip_excel_ingestion_with_non_excel_mime_is_included(self):
        # Counterpart to test_skip_excel_ingestion_mode_is_excluded: a doc
        # with SKIP_EXCEL_INGESTION but a non-Excel mime is considered
        # ingested and must keep the uploaded search tool enabled.
        doc = self._make_doc(
            {"uniqueIngestionMode": "SKIP_EXCEL_INGESTION"},
            mime_type="application/pdf",
        )
        common = self._run([doc])
        tool_names = [t.name for t in common.tool_manager_config.tools]
        assert UploadedSearchTool.name in tool_names

    def test_mixed_docs_tool_added_when_at_least_one_is_ingested(self):
        skip_doc = self._make_doc({"uniqueIngestionMode": "SKIP_INGESTION"})
        real_doc = self._make_doc({"uniqueIngestionMode": "INGESTION"})
        common = self._run([skip_doc, real_doc])
        tool_names = [t.name for t in common.tool_manager_config.tools]
        assert UploadedSearchTool.name in tool_names

    def test_all_skip_docs_tool_not_added(self):
        docs = [
            self._make_doc({"uniqueIngestionMode": "SKIP_INGESTION"}),
            self._make_doc(
                {"uniqueIngestionMode": "SKIP_EXCEL_INGESTION"},
                mime_type="text/csv",
            ),
        ]
        common = self._run(docs)
        tool_names = [t.name for t in common.tool_manager_config.tools]
        assert UploadedSearchTool.name not in tool_names


class TestConfigureUploadedSearchToolForcing:
    def _make_doc(self):
        doc = MagicMock()
        doc.is_expired.return_value = False
        return doc

    def _run(self, docs, tool_choices=None, force=True):
        common_components = _make_common_components(docs)
        event = _make_event(tool_choices or [])
        config = UploadedSearchToolConfig(force=force)
        should_force = _configure_uploaded_search_tool(
            event=event,
            logger=MagicMock(),
            common_components=common_components,
            config=config,
        )
        return should_force, common_components, event

    def test_forces_when_valid_docs_and_force_true(self):
        should_force, _, _ = self._run([self._make_doc()], force=True)
        assert should_force is True

    def test_does_not_force_when_force_false(self):
        should_force, _, _ = self._run([self._make_doc()], force=False)
        assert should_force is False

    def test_does_not_force_when_no_docs(self):
        should_force, _, _ = self._run([], force=True)
        assert should_force is False

    def test_does_not_force_when_tool_choices_already_exist(self):
        # Tool is added to tool_choices for availability instead of being force-called
        should_force, _, event = self._run(
            [self._make_doc()], tool_choices=["InternalSearch"], force=True
        )
        assert should_force is False
        assert UploadedSearchTool.name in event.payload.tool_choices

    def test_tool_not_appended_to_empty_tool_choices(self):
        _, _, event = self._run([self._make_doc()], tool_choices=[], force=True)
        assert event.payload.tool_choices == []
