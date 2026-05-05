from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_orchestrator.config import UniqueAIConfig

MODULE = "unique_orchestrator.unique_ai_builder"
UTILS_MODULE = "unique_orchestrator.utils"


def _make_doc(doc_id: str) -> MagicMock:
    doc = MagicMock()
    doc.id = doc_id
    return doc


def _make_event(
    additional_parameters: MagicMock | None = None,
) -> MagicMock:
    event = MagicMock()
    event.user_id = "user_1"
    event.company_id = "company_1"
    event.payload.assistant_id = "assistant_1"
    event.payload.chat_id = "chat_1"
    event.payload.tool_choices = []
    event.payload.mcp_servers = []
    event.payload.additional_parameters = additional_parameters
    return event


@pytest.fixture
def _patch_constructors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub out heavy service constructors so _build_common runs without real infra."""
    monkeypatch.setattr(f"{MODULE}.ChatService", lambda event: MagicMock())
    monkeypatch.setattr(
        f"{MODULE}.LanguageModelService.from_event", lambda event: MagicMock()
    )
    monkeypatch.setattr(f"{MODULE}.SubAgentResponseWatcher", MagicMock)
    monkeypatch.setattr(f"{MODULE}.ToolProgressReporter", lambda **kw: MagicMock())
    monkeypatch.setattr(f"{MODULE}.ThinkingManager", lambda **kw: MagicMock())
    monkeypatch.setattr(f"{MODULE}.ReferenceManager", MagicMock)
    monkeypatch.setattr(f"{MODULE}.HistoryManager", lambda *a, **kw: MagicMock())
    monkeypatch.setattr(f"{MODULE}.HistoryManagerConfig", lambda **kw: MagicMock())
    monkeypatch.setattr(f"{MODULE}.EvaluationManager", lambda **kw: MagicMock())
    monkeypatch.setattr(f"{MODULE}.MCPManager", lambda **kw: MagicMock())
    monkeypatch.setattr(f"{MODULE}.A2AManager", lambda **kw: MagicMock())
    monkeypatch.setattr(f"{MODULE}.PostprocessorManager", lambda **kw: MagicMock())
    monkeypatch.setattr(f"{MODULE}.MessageStepLogger", lambda *a: MagicMock())


class TestBuildCommonSelectedUploadedFiles:
    """Tests for the selected_uploaded_files filtering in _build_common."""

    @pytest.mark.ai
    async def test_filters_uploaded_documents_when_flag_enabled_and_selection_present(
        self, monkeypatch: pytest.MonkeyPatch, _patch_constructors: None
    ) -> None:
        """
        Purpose: Verify that _build_common filters uploaded documents to the
        selected subset when the feature flag is enabled and a selection exists.
        Why this matters: Users who select specific files must only have those
        files used by the orchestrator; other uploads must be excluded.
        Setup summary: Three docs returned from the async content service;
        only two selected; assert result contains exactly those two.
        """
        from unique_orchestrator.unique_ai_builder import _build_common

        docs = [_make_doc("a"), _make_doc("b"), _make_doc("c")]
        mock_content_service = MagicMock()
        mock_content_service.get_documents_uploaded_to_chat_async = AsyncMock(
            return_value=docs
        )
        monkeypatch.setattr(
            f"{MODULE}.ContentService.from_event", lambda event: mock_content_service
        )

        mock_ff = MagicMock()
        mock_ff.enable_selected_uploaded_files_un_18215.is_enabled.return_value = True
        monkeypatch.setattr(f"{UTILS_MODULE}.feature_flags", mock_ff)

        additional = MagicMock()
        additional.selected_uploaded_files = [MagicMock(id="a"), MagicMock(id="c")]
        additional.selected_uploaded_file_ids = ["a", "c"]
        event = _make_event(additional_parameters=additional)

        result = await _build_common(event, MagicMock(), UniqueAIConfig())

        result_ids = [doc.id for doc in result.uploaded_documents]
        assert result_ids == ["a", "c"]

    @pytest.mark.ai
    async def test_keeps_all_documents_when_additional_parameters_is_none(
        self, monkeypatch: pytest.MonkeyPatch, _patch_constructors: None
    ) -> None:
        """
        Purpose: Verify that _build_common returns all documents when no
        additional_parameters are present.
        Why this matters: Absence of selection parameters must not silently
        discard uploaded files.
        Setup summary: Three docs returned; additional_parameters=None;
        assert all three ids are present in result.
        """
        from unique_orchestrator.unique_ai_builder import _build_common

        docs = [_make_doc("a"), _make_doc("b"), _make_doc("c")]
        mock_content_service = MagicMock()
        mock_content_service.get_documents_uploaded_to_chat_async = AsyncMock(
            return_value=docs
        )
        monkeypatch.setattr(
            f"{MODULE}.ContentService.from_event", lambda event: mock_content_service
        )

        mock_ff = MagicMock()
        mock_ff.enable_selected_uploaded_files_un_18215.is_enabled.return_value = True
        monkeypatch.setattr(f"{UTILS_MODULE}.feature_flags", mock_ff)

        event = _make_event(additional_parameters=None)

        result = await _build_common(event, MagicMock(), UniqueAIConfig())

        result_ids = [doc.id for doc in result.uploaded_documents]
        assert result_ids == ["a", "b", "c"]

    @pytest.mark.ai
    async def test_returns_no_documents_when_selected_uploaded_files_is_empty(
        self, monkeypatch: pytest.MonkeyPatch, _patch_constructors: None
    ) -> None:
        """
        Purpose: Verify that an empty selection list causes _build_common to
        return no uploaded documents.
        Why this matters: Explicitly selecting nothing should honour that choice
        and prevent all uploaded files from being included.
        Setup summary: Two docs available; empty selection; assert result is empty.
        """
        from unique_orchestrator.unique_ai_builder import _build_common

        docs = [_make_doc("a"), _make_doc("b")]
        mock_content_service = MagicMock()
        mock_content_service.get_documents_uploaded_to_chat_async = AsyncMock(
            return_value=docs
        )
        monkeypatch.setattr(
            f"{MODULE}.ContentService.from_event", lambda event: mock_content_service
        )

        mock_ff = MagicMock()
        mock_ff.enable_selected_uploaded_files_un_18215.is_enabled.return_value = True
        monkeypatch.setattr(f"{UTILS_MODULE}.feature_flags", mock_ff)

        additional = MagicMock()
        additional.selected_uploaded_files = []
        additional.selected_uploaded_file_ids = []
        event = _make_event(additional_parameters=additional)

        result = await _build_common(event, MagicMock(), UniqueAIConfig())

        result_ids = [doc.id for doc in result.uploaded_documents]
        assert result_ids == []

    @pytest.mark.ai
    async def test_keeps_all_documents_when_feature_flag_disabled(
        self, monkeypatch: pytest.MonkeyPatch, _patch_constructors: None
    ) -> None:
        """
        Purpose: Verify that _build_common ignores the selection when the
        feature flag is disabled.
        Why this matters: The selection feature is gated; disabling the flag
        must restore the default behaviour of including all uploads.
        Setup summary: Three docs, flag off, only one doc in selection;
        assert all three are returned.
        """
        from unique_orchestrator.unique_ai_builder import _build_common

        docs = [_make_doc("a"), _make_doc("b"), _make_doc("c")]
        mock_content_service = MagicMock()
        mock_content_service.get_documents_uploaded_to_chat_async = AsyncMock(
            return_value=docs
        )
        monkeypatch.setattr(
            f"{MODULE}.ContentService.from_event", lambda event: mock_content_service
        )

        mock_ff = MagicMock()
        mock_ff.enable_selected_uploaded_files_un_18215.is_enabled.return_value = False
        monkeypatch.setattr(f"{UTILS_MODULE}.feature_flags", mock_ff)

        additional = MagicMock()
        additional.selected_uploaded_files = [MagicMock(id="a")]
        additional.selected_uploaded_file_ids = ["a"]
        event = _make_event(additional_parameters=additional)

        result = await _build_common(event, MagicMock(), UniqueAIConfig())

        result_ids = [doc.id for doc in result.uploaded_documents]
        assert result_ids == ["a", "b", "c"]

    @pytest.mark.ai
    async def test_filters_to_single_selected_document(
        self, monkeypatch: pytest.MonkeyPatch, _patch_constructors: None
    ) -> None:
        """
        Purpose: Verify that a single-item selection produces exactly one
        document in _build_common's result.
        Why this matters: Edge case where only one file is selected must not
        accidentally include the others.
        Setup summary: Three docs x/y/z; only y selected; assert result is [y].
        """
        from unique_orchestrator.unique_ai_builder import _build_common

        docs = [_make_doc("x"), _make_doc("y"), _make_doc("z")]
        mock_content_service = MagicMock()
        mock_content_service.get_documents_uploaded_to_chat_async = AsyncMock(
            return_value=docs
        )
        monkeypatch.setattr(
            f"{MODULE}.ContentService.from_event", lambda event: mock_content_service
        )

        mock_ff = MagicMock()
        mock_ff.enable_selected_uploaded_files_un_18215.is_enabled.return_value = True
        monkeypatch.setattr(f"{UTILS_MODULE}.feature_flags", mock_ff)

        additional = MagicMock()
        additional.selected_uploaded_files = [MagicMock(id="y")]
        additional.selected_uploaded_file_ids = ["y"]
        event = _make_event(additional_parameters=additional)

        result = await _build_common(event, MagicMock(), UniqueAIConfig())

        result_ids = [doc.id for doc in result.uploaded_documents]
        assert result_ids == ["y"]

    @pytest.mark.ai
    async def test_uses_async_content_service_method(
        self, monkeypatch: pytest.MonkeyPatch, _patch_constructors: None
    ) -> None:
        """
        Purpose: Verify that _build_common calls get_documents_uploaded_to_chat_async
        rather than the synchronous variant.
        Why this matters: The sync method may block the event loop; the PR
        explicitly migrated the call to the async API.
        Setup summary: Spy on both methods; after _build_common completes,
        assert async was called and sync was not.
        """
        from unique_orchestrator.unique_ai_builder import _build_common

        mock_content_service = MagicMock()
        mock_content_service.get_documents_uploaded_to_chat_async = AsyncMock(
            return_value=[]
        )
        mock_content_service.get_documents_uploaded_to_chat = MagicMock(return_value=[])
        monkeypatch.setattr(
            f"{MODULE}.ContentService.from_event", lambda event: mock_content_service
        )

        mock_ff = MagicMock()
        mock_ff.enable_selected_uploaded_files_un_18215.is_enabled.return_value = False
        monkeypatch.setattr(f"{UTILS_MODULE}.feature_flags", mock_ff)

        event = _make_event(additional_parameters=None)

        await _build_common(event, MagicMock(), UniqueAIConfig())

        mock_content_service.get_documents_uploaded_to_chat_async.assert_awaited_once()
        mock_content_service.get_documents_uploaded_to_chat.assert_not_called()
