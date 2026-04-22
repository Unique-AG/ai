"""Coverage tests for the Skill-tool / tool-reminder integration in UniqueAI.

These tests exercise the *new* code paths added to ``UniqueAI`` when the
Skill tool was introduced:

* ``run()`` preloads ``/skill-name`` invocations before the first
  LLM call.
* ``_compose_message_plan_execution()`` injects per-turn
  ``tool_system_reminder_for_user_prompt`` strings on the latest
  user message.
* ``_log_tool_calls()`` hides ``Skill`` entries from the "Triggered
  Tool Calls" step (the Skill tool emits its own log line per
  invocation).
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelUserMessage,
)

if TYPE_CHECKING:
    from unique_orchestrator.unique_ai import UniqueAI


@pytest.fixture
def mock_unique_ai(monkeypatch: pytest.MonkeyPatch) -> "UniqueAI":
    """Build a UniqueAI instance with heavy dependencies mocked out."""

    mock_service_module = MagicMock()
    mock_service_module.MessageStepLogger = MagicMock()
    monkeypatch.setitem(
        sys.modules,
        "unique_toolkit.agentic.message_log_manager.service",
        mock_service_module,
    )

    from unique_orchestrator.unique_ai import UniqueAI

    dummy_event = MagicMock()
    dummy_event.payload.assistant_message.id = "assist_1"
    dummy_event.payload.user_message.text = "query"
    dummy_event.company_id = "co-1"

    mock_config = MagicMock()
    mock_config.agent.prompt_config.user_metadata = []
    mock_config.agent.experimental.open_file_tool_config.enabled = False
    mock_config.agent.experimental.responses_api_config.use_responses_api = False
    mock_config.agent.experimental.use_responses_api = False

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
        tool_manager=MagicMock(),
        history_manager=MagicMock(),
        evaluation_manager=MagicMock(),
        postprocessor_manager=MagicMock(),
        message_step_logger=MagicMock(),
        mcp_servers=[],
        loop_iteration_runner=MagicMock(),
    )


class TestPreloadSkillsInRun:
    """Covers the ``preload_invoked_skills`` call site in ``UniqueAI.run``."""

    @pytest.mark.asyncio
    async def test_stripped_text_replaces_user_message(
        self, mock_unique_ai: "UniqueAI"
    ) -> None:
        """When preload returns stripped text, the user message is overwritten."""
        mock_unique_ai._event.payload.user_message.text = "/foo the real query"

        with (
            patch(
                "unique_orchestrator.unique_ai.preload_invoked_skills",
                new=AsyncMock(return_value="the real query"),
            ),
            patch(
                "unique_orchestrator.unique_ai.feature_flags"
            ) as mock_feature_flags,
        ):
            mock_feature_flags.enable_new_answers_ui_un_14411.is_enabled.return_value = True
            mock_unique_ai._chat_service.cancellation.on_cancellation.subscribe = (
                MagicMock(return_value=MagicMock())
            )
            mock_unique_ai._chat_service.cancellation.on_cancellation.unsubscribe = (
                MagicMock()
            )
            mock_unique_ai._chat_service.cancellation.check_cancellation_async = (
                AsyncMock(return_value=True)
            )
            # Short-circuit ``run`` immediately by treating the loop as cancelled
            # after preload runs.
            await mock_unique_ai.run()

        assert mock_unique_ai._event.payload.user_message.text == "the real query"

    @pytest.mark.asyncio
    async def test_no_skills_leaves_user_message_untouched(
        self, mock_unique_ai: "UniqueAI"
    ) -> None:
        """When preload returns None, the user message is not touched."""
        mock_unique_ai._event.payload.user_message.text = "plain question"

        with (
            patch(
                "unique_orchestrator.unique_ai.preload_invoked_skills",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "unique_orchestrator.unique_ai.feature_flags"
            ) as mock_feature_flags,
        ):
            mock_feature_flags.enable_new_answers_ui_un_14411.is_enabled.return_value = True
            mock_unique_ai._chat_service.cancellation.on_cancellation.subscribe = (
                MagicMock(return_value=MagicMock())
            )
            mock_unique_ai._chat_service.cancellation.on_cancellation.unsubscribe = (
                MagicMock()
            )
            mock_unique_ai._chat_service.cancellation.check_cancellation_async = (
                AsyncMock(return_value=True)
            )
            await mock_unique_ai.run()

        assert mock_unique_ai._event.payload.user_message.text == "plain question"


class TestComposeMessagePlanExecutionReminders:
    """Covers the tool-reminders block in ``_compose_message_plan_execution``."""

    def _wire_compose_deps(self, ua: "UniqueAI", user_text: str = "hi") -> None:
        ua._event.payload.user_message.text = user_text
        ua._render_user_prompt = AsyncMock(return_value="rendered-user")  # type: ignore[method-assign]
        ua._render_system_prompt = AsyncMock(return_value="rendered-system")  # type: ignore[method-assign]
        ua._history_manager.get_history_for_model_call = AsyncMock(
            return_value=LanguageModelMessages(
                [LanguageModelUserMessage(content=user_text)]
            )
        )
        ua._postprocessor_manager.remove_from_text = MagicMock()

    @pytest.mark.asyncio
    async def test_tool_reminder_is_prepended_to_user_message(
        self, mock_unique_ai: "UniqueAI"
    ) -> None:
        self._wire_compose_deps(mock_unique_ai, user_text="commit the change")

        reminder_prompts = MagicMock()
        reminder_prompts.tool_system_reminder_for_user_prompt = (
            "<system-reminder>skills: /commit</system-reminder>"
        )
        mock_unique_ai._tool_manager.get_tool_prompts = MagicMock(
            return_value=[reminder_prompts]
        )

        messages = await mock_unique_ai._compose_message_plan_execution()

        assert len(messages.root) == 1
        content = messages.root[0].content
        assert isinstance(content, list)
        assert content[0]["text"] == (  # type: ignore[index]
            "<system-reminder>skills: /commit</system-reminder>"
        )
        assert content[1]["text"] == "commit the change"  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_empty_reminders_leave_message_unchanged(
        self, mock_unique_ai: "UniqueAI"
    ) -> None:
        self._wire_compose_deps(mock_unique_ai, user_text="hello")

        empty_prompts = MagicMock()
        empty_prompts.tool_system_reminder_for_user_prompt = ""
        mock_unique_ai._tool_manager.get_tool_prompts = MagicMock(
            return_value=[empty_prompts]
        )

        messages = await mock_unique_ai._compose_message_plan_execution()

        assert messages.root[0].content == "hello"


class TestLogToolCallsExcludesSkill:
    """Covers the ``Skill`` entry added to ``tool_names_not_to_log``."""

    def test_skill_tool_is_not_logged_but_kept_in_history(
        self, mock_unique_ai: "UniqueAI"
    ) -> None:
        mock_tool = MagicMock(spec=["name", "display_name"])
        mock_tool.name = "Skill"
        mock_tool.display_name.return_value = "Skill"

        mock_unique_ai._tool_manager.available_tools = [mock_tool]

        mock_tool_call = MagicMock(spec=["name"])
        mock_tool_call.name = "Skill"

        mock_unique_ai._log_tool_calls([mock_tool_call])

        mock_unique_ai._history_manager.add_tool_call.assert_called_once_with(
            mock_tool_call
        )
        mock_unique_ai._message_step_logger.create_message_log_entry.assert_not_called()

    def test_skill_and_other_tools_mixed(self, mock_unique_ai: "UniqueAI") -> None:
        skill_tool = MagicMock(spec=["name", "display_name"])
        skill_tool.name = "Skill"
        skill_tool.display_name.return_value = "Skill"

        other = MagicMock(spec=["name", "display_name"])
        other.name = "search"
        other.display_name.return_value = "Search"

        mock_unique_ai._tool_manager.available_tools = [skill_tool, other]

        skill_call = MagicMock(spec=["name"])
        skill_call.name = "Skill"
        other_call = MagicMock(spec=["name"])
        other_call.name = "search"

        mock_unique_ai._log_tool_calls([skill_call, other_call])

        assert mock_unique_ai._history_manager.add_tool_call.call_count == 2
        mock_unique_ai._message_step_logger.create_message_log_entry.assert_called_once_with(
            text="**Triggered Tool Calls:**\n - Search", references=[]
        )
