"""Tests for ClaudeAgentRunner routing in build_unique_ai / _build_claude_agent.

Verifies that:
- ExperimentalConfig.claude_agent_config defaults to None
- Setting claude_agent_config routes to _build_claude_agent instead of UniqueAI paths
- Claude agent route takes priority over responses_api route
- _build_claude_agent passes the correct components to ClaudeAgentRunner
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unique_orchestrator.config import ExperimentalConfig, UniqueAIConfig
from unique_orchestrator.unique_ai_builder import _build_claude_agent


def _make_claude_agent_module() -> tuple[MagicMock, MagicMock]:
    """Return (fake_module, MockClaudeAgentRunner) for use in sys.modules patching.

    _build_claude_agent does a lazy 'from unique_toolkit.agentic.claude_agent import
    ClaudeAgentRunner' — this bypasses the hard dep before the toolkit is published.
    We inject a fake module so the tests work without unique_toolkit installed.
    """
    mock_cls = MagicMock(name="ClaudeAgentRunner")
    fake_module = MagicMock()
    fake_module.ClaudeAgentRunner = mock_cls
    return fake_module, mock_cls


# ─────────────────────────────────────────────────────────────────────────────
# ExperimentalConfig field tests — no mocking needed
# ─────────────────────────────────────────────────────────────────────────────


class TestExperimentalConfigClaudeAgentField:
    @pytest.mark.ai
    def test_claude_agent_config__defaults_to_none(self) -> None:
        """ExperimentalConfig.claude_agent_config is None by default."""
        config = ExperimentalConfig()
        assert config.claude_agent_config is None

    @pytest.mark.ai
    def test_claude_agent_config__accepts_arbitrary_value(self) -> None:
        """ExperimentalConfig.claude_agent_config stores any assigned value (Any type)."""
        sentinel = object()
        config = ExperimentalConfig(claude_agent_config=sentinel)
        assert config.claude_agent_config is sentinel


# ─────────────────────────────────────────────────────────────────────────────
# _build_claude_agent unit tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildClaudeAgent:
    @pytest.mark.ai
    def test_build_claude_agent__calls_runner_constructor(self) -> None:
        """_build_claude_agent invokes ClaudeAgentRunner with the correct arguments."""
        mock_claude_config = MagicMock(name="ClaudeAgentConfig")
        config = UniqueAIConfig()
        config.agent.experimental.claude_agent_config = mock_claude_config

        common = MagicMock(name="CommonComponents")
        event = MagicMock(name="ChatEvent")
        logger = MagicMock(name="Logger")
        debug_info = MagicMock(name="DebugInfoManager")

        fake_module, mock_runner_cls = _make_claude_agent_module()
        with patch.dict(
            sys.modules, {"unique_toolkit.agentic.claude_agent": fake_module}
        ):
            result = _build_claude_agent(
                event=event,
                logger=logger,
                config=config,
                common_components=common,
                debug_info_manager=debug_info,
            )

        mock_runner_cls.assert_called_once_with(
            event=event,
            logger=logger,
            config=config,
            claude_config=mock_claude_config,
            chat_service=common.chat_service,
            content_service=common.content_service,
            evaluation_manager=common.evaluation_manager,
            postprocessor_manager=common.postprocessor_manager,
            reference_manager=common.reference_manager,
            thinking_manager=common.thinking_manager,
            tool_progress_reporter=common.tool_progress_reporter,
            message_step_logger=common.message_step_logger,
            history_manager=common.history_manager,
            debug_info_manager=debug_info,
        )
        assert result is mock_runner_cls.return_value

    @pytest.mark.ai
    def test_build_claude_agent__raises_if_config_is_none(self) -> None:
        """_build_claude_agent asserts claude_agent_config is not None."""
        config = UniqueAIConfig()
        assert config.agent.experimental.claude_agent_config is None

        fake_module, _ = _make_claude_agent_module()
        with patch.dict(
            sys.modules, {"unique_toolkit.agentic.claude_agent": fake_module}
        ):
            with pytest.raises(AssertionError):
                _build_claude_agent(
                    event=MagicMock(),
                    logger=MagicMock(),
                    config=config,
                    common_components=MagicMock(),
                    debug_info_manager=MagicMock(),
                )


# ─────────────────────────────────────────────────────────────────────────────
# build_unique_ai routing tests
# ─────────────────────────────────────────────────────────────────────────────


def _make_event() -> MagicMock:
    event = MagicMock(name="ChatEvent")
    event.company_id = "test-company"
    event.user_id = "test-user"
    event.payload.chat_id = "test-chat"
    event.payload.assistant_id = "test-assistant"
    event.payload.mcp_servers = []
    event.payload.assistant_message.id = "test-msg"
    event.payload.user_metadata = None
    return event


class TestBuildUniqueAiRouting:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_routes_to_claude_agent__when_claude_agent_config_set(self) -> None:
        """build_unique_ai returns ClaudeAgentRunner when claude_agent_config is set."""
        from unique_orchestrator.unique_ai_builder import build_unique_ai

        config = UniqueAIConfig()
        config.agent.experimental.claude_agent_config = MagicMock(
            name="ClaudeAgentConfig"
        )

        fake_module, mock_runner_cls = _make_claude_agent_module()
        with (
            patch(
                "unique_orchestrator.unique_ai_builder._build_common",
                return_value=MagicMock(),
            ),
            patch.dict(
                sys.modules, {"unique_toolkit.agentic.claude_agent": fake_module}
            ),
        ):
            result = await build_unique_ai(
                event=_make_event(),
                logger=MagicMock(),
                config=config,
                debug_info_manager=MagicMock(),
            )

        assert result is mock_runner_cls.return_value
        mock_runner_cls.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_claude_agent_takes_priority_over_responses_api(self) -> None:
        """Claude agent route wins when both claude_agent_config and use_responses_api are set."""
        from unique_orchestrator.unique_ai_builder import build_unique_ai

        config = UniqueAIConfig()
        config.agent.experimental.claude_agent_config = MagicMock(
            name="ClaudeAgentConfig"
        )
        config.agent.experimental.responses_api_config.use_responses_api = True

        fake_module, mock_runner_cls = _make_claude_agent_module()
        mock_build_responses = AsyncMock(name="_build_responses")

        with (
            patch(
                "unique_orchestrator.unique_ai_builder._build_common",
                return_value=MagicMock(),
            ),
            patch.dict(
                sys.modules, {"unique_toolkit.agentic.claude_agent": fake_module}
            ),
            patch(
                "unique_orchestrator.unique_ai_builder._build_responses",
                mock_build_responses,
            ),
        ):
            result = await build_unique_ai(
                event=_make_event(),
                logger=MagicMock(),
                config=config,
                debug_info_manager=MagicMock(),
            )

        assert result is mock_runner_cls.return_value
        mock_runner_cls.assert_called_once()
        mock_build_responses.assert_not_called()
