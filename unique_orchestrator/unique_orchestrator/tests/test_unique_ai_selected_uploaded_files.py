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


class TestRenderSystemPromptSelectedUploadedFiles:
    """Tests for the selected_uploaded_files filtering in _render_system_prompt (lines 482-487)."""

    @pytest.fixture
    def mock_unique_ai(self, monkeypatch: pytest.MonkeyPatch) -> UniqueAI:
        from unique_orchestrator.unique_ai import UniqueAI

        mock_feature_flags = MagicMock()
        monkeypatch.setattr(
            "unique_orchestrator.unique_ai.feature_flags", mock_feature_flags
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
        mock_content_service.get_documents_uploaded_to_chat.return_value = []

        ua = UniqueAI(
            logger=mock_logger,
            event=dummy_event,
            config=mock_config,
            chat_service=MagicMock(),
            content_service=mock_content_service,
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
    async def test_filters_uploaded_documents_to_selected_ids(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        docs = [_make_expired_doc("a"), _make_expired_doc("b"), _make_expired_doc("c")]
        mock_unique_ai._content_service.get_documents_uploaded_to_chat.return_value = (
            docs
        )

        flag = mock_unique_ai._event.company_id
        ff = mock_unique_ai._config  # access via the monkeypatched module
        # Enable the feature flag
        from unique_orchestrator.unique_ai import feature_flags

        feature_flags.enable_selected_uploaded_files_un_18470.is_enabled.return_value = (
            True
        )

        additional = MagicMock()
        additional.selected_uploaded_files = ["a", "c"]
        mock_unique_ai._event.payload.additional_parameters = additional

        result = await mock_unique_ai._render_system_prompt()
        assert result == "2"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_no_filtering_when_additional_parameters_is_none(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        docs = [_make_expired_doc("a"), _make_expired_doc("b"), _make_expired_doc("c")]
        mock_unique_ai._content_service.get_documents_uploaded_to_chat.return_value = (
            docs
        )

        from unique_orchestrator.unique_ai import feature_flags

        feature_flags.enable_selected_uploaded_files_un_18470.is_enabled.return_value = (
            True
        )

        mock_unique_ai._event.payload.additional_parameters = None

        result = await mock_unique_ai._render_system_prompt()
        assert result == "3"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_no_filtering_when_selected_uploaded_files_is_empty(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        docs = [_make_expired_doc("a"), _make_expired_doc("b")]
        mock_unique_ai._content_service.get_documents_uploaded_to_chat.return_value = (
            docs
        )

        from unique_orchestrator.unique_ai import feature_flags

        feature_flags.enable_selected_uploaded_files_un_18470.is_enabled.return_value = (
            True
        )

        additional = MagicMock()
        additional.selected_uploaded_files = []
        mock_unique_ai._event.payload.additional_parameters = additional

        result = await mock_unique_ai._render_system_prompt()
        assert result == "2"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_no_filtering_when_feature_flag_disabled(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        docs = [_make_expired_doc("a"), _make_expired_doc("b"), _make_expired_doc("c")]
        mock_unique_ai._content_service.get_documents_uploaded_to_chat.return_value = (
            docs
        )

        from unique_orchestrator.unique_ai import feature_flags

        feature_flags.enable_selected_uploaded_files_un_18470.is_enabled.return_value = (
            False
        )

        additional = MagicMock()
        additional.selected_uploaded_files = ["a"]
        mock_unique_ai._event.payload.additional_parameters = additional

        result = await mock_unique_ai._render_system_prompt()
        assert result == "3"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_filters_to_single_selected_document(
        self, mock_unique_ai: UniqueAI
    ) -> None:
        docs = [_make_expired_doc("x"), _make_expired_doc("y"), _make_expired_doc("z")]
        mock_unique_ai._content_service.get_documents_uploaded_to_chat.return_value = (
            docs
        )

        from unique_orchestrator.unique_ai import feature_flags

        feature_flags.enable_selected_uploaded_files_un_18470.is_enabled.return_value = (
            True
        )

        additional = MagicMock()
        additional.selected_uploaded_files = ["y"]
        mock_unique_ai._event.payload.additional_parameters = additional

        result = await mock_unique_ai._render_system_prompt()
        assert result == "1"
