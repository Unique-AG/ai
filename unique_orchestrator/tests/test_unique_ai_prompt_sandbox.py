"""Configurable prompt templates render through the shared Jinja sandbox."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from jinja2.exceptions import SecurityError

if TYPE_CHECKING:
    from unique_orchestrator.unique_ai import UniqueAI

SSTI_PAYLOAD = "{{ namespace.__init__.__globals__.os.popen('id').read() }}"


@pytest.fixture
def unique_ai(monkeypatch: pytest.MonkeyPatch) -> "UniqueAI":
    mock_service_module = MagicMock()
    mock_service_module.MessageStepLogger = MagicMock()
    monkeypatch.setitem(
        sys.modules,
        "unique_toolkit.agentic.message_log_manager.service",
        mock_service_module,
    )

    from unique_orchestrator.unique_ai import UniqueAI

    event = MagicMock()
    event.payload.user_message.text = "query"
    event.payload.skill_choices = []

    config = MagicMock()
    config.agent.prompt_config.user_metadata = []
    config.agent.experimental.sub_agents_config.referencing_config = None
    config.agent.experimental.open_file_tool_config.enabled = False
    config.space.custom_instructions = "be nice"
    config.space.user_space_instructions = ""
    config.space.project_name = "Unique"
    config.space.language_model.model_dump.return_value = {"name": "model"}

    tool_manager = MagicMock()
    tool_manager.get_tool_prompts.return_value = []
    tool_manager.filter_tool_calls.return_value = []

    history_manager = MagicMock()
    history_manager.get_tool_calls.return_value = []

    return UniqueAI(
        logger=MagicMock(),
        event=event,
        config=config,
        chat_service=MagicMock(),
        content_service=MagicMock(),
        debug_info_manager=MagicMock(),
        streaming_handler=MagicMock(),
        reference_manager=MagicMock(),
        thinking_manager=MagicMock(),
        tool_manager=tool_manager,
        history_manager=history_manager,
        evaluation_manager=MagicMock(),
        postprocessor_manager=MagicMock(),
        message_step_logger=MagicMock(),
        mcp_servers=[],
        loop_iteration_runner=MagicMock(),
    )


@pytest.mark.ai
class TestPromptTemplatesAreSandboxed:
    @pytest.mark.asyncio
    async def test_system_prompt_rejects_ssti_payload(
        self, unique_ai: "UniqueAI"
    ) -> None:
        unique_ai._config.agent.prompt_config.system_prompt_template = SSTI_PAYLOAD

        with pytest.raises(SecurityError):
            await unique_ai._render_system_prompt()

    @pytest.mark.asyncio
    async def test_user_prompt_rejects_ssti_payload(
        self, unique_ai: "UniqueAI"
    ) -> None:
        unique_ai._config.agent.prompt_config.user_message_prompt_template = (
            SSTI_PAYLOAD
        )

        with pytest.raises(SecurityError):
            await unique_ai._render_user_prompt()

    @pytest.mark.asyncio
    async def test_system_prompt_renders_context_variables(
        self, unique_ai: "UniqueAI"
    ) -> None:
        unique_ai._config.agent.prompt_config.system_prompt_template = (
            "{{ project_name }}: {{ custom_instructions }}"
        )

        assert await unique_ai._render_system_prompt() == "Unique: be nice"

    @pytest.mark.asyncio
    async def test_user_prompt_renders_query(self, unique_ai: "UniqueAI") -> None:
        unique_ai._config.agent.prompt_config.user_message_prompt_template = (
            "Q: {{ query }}"
        )

        assert await unique_ai._render_user_prompt() == "Q: query"
