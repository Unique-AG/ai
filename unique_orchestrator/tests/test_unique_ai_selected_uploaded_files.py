from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from unique_orchestrator.unique_ai import UniqueAI


def _make_expired_doc(doc_id: str) -> MagicMock:
    doc = MagicMock()
    doc.id = doc_id
    doc.expired_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
    return doc


class TestRenderSystemPromptUploadedDocumentsExpired:
    """Tests for uploaded_documents_expired rendering in _render_system_prompt.

    _render_system_prompt builds uploaded_documents_expired by filtering
    self._uploaded_documents through doc.is_expired(). These tests verify
    that the Jinja template variable reflects the correct count based on
    what is stored in _uploaded_documents.
    """

    @pytest.fixture
    def mock_unique_ai(self, monkeypatch: pytest.MonkeyPatch) -> UniqueAI:
        from unique_orchestrator.unique_ai import UniqueAI

        mock_feature_flags = MagicMock()
        monkeypatch.setattr(
            "unique_orchestrator.utils.feature_flags", mock_feature_flags
        )

        mock_logger = MagicMock()

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

        mock_tool_manager = MagicMock()
        mock_tool_manager.get_tool_prompts.return_value = []
        mock_tool_manager.filter_tool_calls.return_value = []

        mock_history_manager = MagicMock()
        mock_history_manager.get_tool_calls.return_value = []

        mock_content_service = MagicMock()

        ua = UniqueAI(
            logger=mock_logger,
            event=dummy_event,
            config=mock_config,
            chat_service=MagicMock(),
            content_service=mock_content_service,
            uploaded_documents=[],
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
        )
        return ua

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_expired_docs_in_uploaded_documents_are_counted(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that expired docs in _uploaded_documents are included in
                 uploaded_documents_expired passed to the system prompt template.
        Why this matters: The template uses uploaded_documents_expired to render expiry
                          warnings — every expired document must be counted.
        Setup summary: Assign three MagicMock docs (all expired via truthy is_expired())
                       to _uploaded_documents; assert the template renders "3".
        """
        docs = [_make_expired_doc("a"), _make_expired_doc("b"), _make_expired_doc("c")]
        mock_unique_ai._uploaded_documents = docs

        result = await mock_unique_ai._render_system_prompt()
        assert result == "3"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_empty_uploaded_documents_yields_zero_expired(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that an empty _uploaded_documents list results in zero
                 expired documents in the template.
        Why this matters: When no documents are uploaded, the template must render "0"
                          rather than failing or returning stale data.
        Setup summary: Leave _uploaded_documents as [] (set in fixture); assert "0".
        """
        mock_unique_ai._uploaded_documents = []

        result = await mock_unique_ai._render_system_prompt()
        assert result == "0"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_non_expired_docs_are_not_counted(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that docs whose is_expired() returns False are excluded from
                 the uploaded_documents_expired list.
        Why this matters: Valid (non-expired) documents must not inflate the expired
                          count seen by the template.
        Setup summary: Assign one MagicMock configured to return False from is_expired()
                       to _uploaded_documents; assert template renders "0".
        """
        non_expired_doc = MagicMock()
        non_expired_doc.id = "valid_doc"
        non_expired_doc.is_expired.return_value = False
        mock_unique_ai._uploaded_documents = [non_expired_doc]

        result = await mock_unique_ai._render_system_prompt()
        assert result == "0"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_only_expired_docs_counted_in_mixed_list(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify that only expired docs are counted when _uploaded_documents
                 contains a mix of expired and valid documents.
        Why this matters: The template must accurately reflect how many documents have
                          expired, not the total document count.
        Setup summary: Assign two expired MagicMock docs and one non-expired MagicMock
                       doc to _uploaded_documents; assert template renders "2".
        """
        expired_doc_1 = _make_expired_doc("x")
        expired_doc_2 = _make_expired_doc("y")
        non_expired_doc = MagicMock()
        non_expired_doc.id = "z"
        non_expired_doc.is_expired.return_value = False
        mock_unique_ai._uploaded_documents = [
            expired_doc_1,
            expired_doc_2,
            non_expired_doc,
        ]

        result = await mock_unique_ai._render_system_prompt()
        assert result == "2"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_single_expired_doc_in_uploaded_documents(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        """
        Purpose: Verify boundary case of exactly one expired document.
        Why this matters: Single-item lists are a common edge case that could expose
                          off-by-one bugs in the filter comprehension.
        Setup summary: Assign one expired MagicMock doc to _uploaded_documents;
                       assert template renders "1".
        """
        mock_unique_ai._uploaded_documents = [_make_expired_doc("only")]

        result = await mock_unique_ai._render_system_prompt()
        assert result == "1"
