from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from unique_orchestrator.unique_ai import UniqueAI


def _make_doc(doc_id: str, *, expired: bool = False) -> MagicMock:
    doc = MagicMock()
    doc.id = doc_id
    doc.is_expired.return_value = expired
    return doc


def _make_unique_ai(
    monkeypatch: pytest.MonkeyPatch,
    uploaded_documents: list | None = None,
) -> UniqueAI:
    from unique_orchestrator.unique_ai import UniqueAI

    monkeypatch.setattr("unique_orchestrator.utils.feature_flags", MagicMock())

    mock_tool_manager = MagicMock()
    mock_tool_manager.get_tool_prompts.return_value = []
    mock_tool_manager.filter_tool_calls.return_value = []

    mock_history_manager = MagicMock()
    mock_history_manager.get_tool_calls.return_value = []

    dummy_event = MagicMock()
    dummy_event.payload.assistant_message.id = "assist_1"
    dummy_event.payload.user_message.text = "query"
    dummy_event.payload.user_metadata = None
    dummy_event.company_id = "company_1"
    dummy_event.payload.additional_parameters = None

    mock_config = MagicMock()
    mock_config.agent.prompt_config.user_metadata = []
    mock_config.agent.prompt_config.system_prompt_template = (
        "{{ uploaded_documents_expired | length }}"
    )
    mock_config.agent.experimental.sub_agents_config.referencing_config = None
    mock_config.agent.experimental.loop_configuration.max_tool_calls_per_iteration = 5
    mock_config.agent.max_loop_iterations = 8
    mock_config.space.language_model.model_dump.return_value = {}
    mock_config.space.project_name = "TestProject"
    mock_config.space.custom_instructions = ""
    mock_config.space.user_space_instructions = None

    return UniqueAI(
        logger=MagicMock(),
        event=dummy_event,
        config=mock_config,
        chat_service=MagicMock(),
        content_service=MagicMock(),
        debug_info_manager=MagicMock(),
        streaming_handler=MagicMock(),
        reference_manager=MagicMock(),
        thinking_manager=MagicMock(),
        tool_manager=mock_tool_manager,
        history_manager=mock_history_manager,
        evaluation_manager=MagicMock(),
        postprocessor_manager=MagicMock(),
        message_step_logger=MagicMock(),
        mcp_servers=[],
        loop_iteration_runner=MagicMock(),
        uploaded_documents=uploaded_documents,
    )


class TestUniqueAIUploadedDocumentsInit:
    """Tests for uploaded_documents injection in UniqueAI.__init__."""

    @pytest.mark.ai
    def test_stores_uploaded_documents_on_instance(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: Verify that UniqueAI stores the injected uploaded_documents
        list on self._uploaded_documents.
        Why this matters: Downstream methods rely on self._uploaded_documents;
        if the constructor doesn't store it the feature silently breaks.
        Setup summary: Pass two doc mocks via constructor; read _uploaded_documents.
        """
        docs = [_make_doc("a"), _make_doc("b")]
        ua = _make_unique_ai(monkeypatch, uploaded_documents=docs)
        assert ua._uploaded_documents is docs

    @pytest.mark.ai
    def test_defaults_to_empty_list_when_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: Verify that passing uploaded_documents=None defaults to [].
        Why this matters: Callers that omit the parameter must not trigger
        AttributeError or NoneType iteration errors later.
        Setup summary: Create UniqueAI with uploaded_documents=None; assert
        _uploaded_documents equals [].
        """
        ua = _make_unique_ai(monkeypatch, uploaded_documents=None)
        assert ua._uploaded_documents == []


class TestRenderSystemPromptUploadedDocumentsExpired:
    """Tests for expired-document detection in _render_system_prompt."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_no_uploaded_documents__renders_zero_expired(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: Verify that an empty uploaded_documents list produces
        uploaded_documents_expired length of zero in the rendered prompt.
        Why this matters: Default state must not surface spurious expired-file
        warnings to the LLM.
        Setup summary: UniqueAI constructed with no uploaded docs; assert
        rendered template equals "0".
        """
        ua = _make_unique_ai(monkeypatch, uploaded_documents=[])
        result = await ua._render_system_prompt()
        assert result == "0"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_non_expired_documents__renders_zero_expired(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: Verify that non-expired documents are not counted as expired
        in the rendered prompt.
        Why this matters: Valid docs must never be flagged as expired, which
        would suppress search over uploaded content.
        Setup summary: Three docs all returning is_expired()=False; assert "0".
        """
        docs = [
            _make_doc("a", expired=False),
            _make_doc("b", expired=False),
            _make_doc("c", expired=False),
        ]
        ua = _make_unique_ai(monkeypatch, uploaded_documents=docs)
        result = await ua._render_system_prompt()
        assert result == "0"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_some_expired_documents__renders_correct_count(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: Verify that only expired documents are counted in the
        uploaded_documents_expired template variable.
        Why this matters: The prompt uses this count to warn the LLM; wrong
        counts mislead it about which files are available.
        Setup summary: Three docs, two expired; assert rendered template is "2".
        """
        docs = [
            _make_doc("a", expired=True),
            _make_doc("b", expired=False),
            _make_doc("c", expired=True),
        ]
        ua = _make_unique_ai(monkeypatch, uploaded_documents=docs)
        result = await ua._render_system_prompt()
        assert result == "2"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_all_expired_documents__renders_all_as_expired(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: Verify that all expired documents are counted when every
        upload has expired.
        Why this matters: Boundary case where every file is stale; the LLM
        must be told none are usable.
        Setup summary: Two expired docs; assert rendered template equals "2".
        """
        docs = [_make_doc("x", expired=True), _make_doc("y", expired=True)]
        ua = _make_unique_ai(monkeypatch, uploaded_documents=docs)
        result = await ua._render_system_prompt()
        assert result == "2"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_uses_is_expired_method_not_expired_at_field(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: Verify that _render_system_prompt delegates expiry decisions
        to doc.is_expired() rather than comparing expired_at directly.
        Why this matters: is_expired() encapsulates timezone-aware logic; bypassing
        it with direct field access would silently break for docs that customise
        expiry semantics.
        Setup summary: Create a doc whose is_expired() returns True but expired_at
        is None; assert the doc is counted as expired.
        """
        doc = MagicMock()
        doc.is_expired.return_value = True
        doc.expired_at = None  # would be treated as non-expired by old field check
        ua = _make_unique_ai(monkeypatch, uploaded_documents=[doc])
        result = await ua._render_system_prompt()
        assert result == "1"
