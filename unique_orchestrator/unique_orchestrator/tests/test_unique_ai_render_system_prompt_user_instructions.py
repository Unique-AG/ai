from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    from unique_orchestrator.unique_ai import UniqueAI


class TestRenderSystemPromptUserInstructions:
    """Test suite for user_instructions merging in UniqueAI._render_system_prompt"""

    @pytest.fixture
    def mock_unique_ai(self) -> "UniqueAI":
        """Create a minimal UniqueAI instance with mocked dependencies
        and a Jinja template that outputs custom_instructions verbatim."""
        from unique_orchestrator.unique_ai import UniqueAI

        mock_logger = MagicMock()

        dummy_event = MagicMock()
        dummy_event.payload.assistant_message.id = "assist_1"
        dummy_event.payload.user_message.text = "query"
        dummy_event.payload.user_metadata = None

        mock_config = MagicMock()
        mock_config.agent.prompt_config.user_metadata = []
        mock_config.agent.prompt_config.system_prompt_template = (
            "{{ custom_instructions }}"
        )
        mock_config.agent.experimental.sub_agents_config.referencing_config = None
        mock_config.agent.experimental.loop_configuration.max_tool_calls_per_iteration = 5
        mock_config.agent.max_loop_iterations = 8
        mock_config.space.language_model.model_dump.return_value = {}
        mock_config.space.project_name = "TestProject"
        mock_config.space.custom_instructions = "System admin instructions."
        mock_config.space.user_instructions = None

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
    async def test_renders_only_custom_instructions_when_user_instructions_is_none(
        self, mock_unique_ai: "UniqueAI"
    ) -> None:
        mock_unique_ai._config.space.custom_instructions = "Admin rules."
        mock_unique_ai._config.space.user_instructions = None

        result = await mock_unique_ai._render_system_prompt()

        assert result == "Admin rules."

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_renders_only_custom_instructions_when_user_instructions_is_empty_string(
        self, mock_unique_ai: "UniqueAI"
    ) -> None:
        mock_unique_ai._config.space.custom_instructions = "Admin rules."
        mock_unique_ai._config.space.user_instructions = ""

        result = await mock_unique_ai._render_system_prompt()

        assert result == "Admin rules."

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_appends_user_instructions_when_present(
        self, mock_unique_ai: "UniqueAI"
    ) -> None:
        mock_unique_ai._config.space.custom_instructions = "Admin rules."
        mock_unique_ai._config.space.user_instructions = "Please respond in French."

        result = await mock_unique_ai._render_system_prompt()

        expected = (
            "Admin rules."
            "\n\nAdditional instructions provided by the user:\n"
            "Please respond in French."
        )
        assert result == expected

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_appends_user_instructions_when_custom_instructions_is_empty(
        self, mock_unique_ai: "UniqueAI"
    ) -> None:
        mock_unique_ai._config.space.custom_instructions = ""
        mock_unique_ai._config.space.user_instructions = "Be concise."

        result = await mock_unique_ai._render_system_prompt()

        expected = (
            "\n\nAdditional instructions provided by the user:\n"
            "Be concise."
        )
        assert result == expected

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_combined_instructions_preserve_multiline_user_instructions(
        self, mock_unique_ai: "UniqueAI"
    ) -> None:
        mock_unique_ai._config.space.custom_instructions = "Base prompt."
        mock_unique_ai._config.space.user_instructions = (
            "Line one.\nLine two.\nLine three."
        )

        result = await mock_unique_ai._render_system_prompt()

        expected = (
            "Base prompt."
            "\n\nAdditional instructions provided by the user:\n"
            "Line one.\nLine two.\nLine three."
        )
        assert result == expected

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_no_mutation_when_both_are_empty_or_none(
        self, mock_unique_ai: "UniqueAI"
    ) -> None:
        mock_unique_ai._config.space.custom_instructions = ""
        mock_unique_ai._config.space.user_instructions = None

        result = await mock_unique_ai._render_system_prompt()

        assert result == ""
