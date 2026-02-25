"""
Tests for Claude Agent SDK routing in build_unique_ai() and ExperimentalConfig.

Verifies that:
1. build_unique_ai() routes to _build_claude_agent() when claude_agent_config is set.
2. Existing responses_api / completions routing is unchanged when claude_agent_config is None.
3. ExperimentalConfig accepts the claude_agent_config field and defaults to None.

All tests use mocks — no real platform event, SDK call, or network access needed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from unique_toolkit.agentic.claude_agent import ClaudeAgentConfig, ClaudeAgentRunner

from unique_orchestrator.config import ExperimentalConfig, UniqueAIConfig

# ─────────────────────────────────────────────────────────────────────────────
# ExperimentalConfig field
# ─────────────────────────────────────────────────────────────────────────────


class TestClaudeAgentConfigInExperimentalConfig:
    def test_experimental_config_accepts_claude_agent_config_field__defaults_to_none(
        self,
    ) -> None:
        """ExperimentalConfig.claude_agent_config defaults to None (explicit opt-in only)."""
        config = ExperimentalConfig()
        assert config.claude_agent_config is None

    def test_experimental_config_accepts_claude_agent_config__when_set(self) -> None:
        """ExperimentalConfig accepts a ClaudeAgentConfig instance."""
        claude_config = ClaudeAgentConfig()
        config = ExperimentalConfig(claude_agent_config=claude_config)
        assert config.claude_agent_config is claude_config
        assert config.claude_agent_config.model == "claude-sonnet-4-20250514"

    def test_experimental_config_claude_agent_config__does_not_auto_enable__when_none(
        self,
    ) -> None:
        """Confirm there is no model validator that auto-enables claude_agent_config.

        Decision B6: Claude Agent SDK is explicit opt-in only. Regular Anthropic model
        names must never trigger the Claude Agent route. This test guards against
        accidental re-introduction of a model-driven auto-enable validator.
        """
        full_config = UniqueAIConfig()
        # Verify that even after all model validators run, claude_agent_config stays None
        assert full_config.agent.experimental.claude_agent_config is None


# ─────────────────────────────────────────────────────────────────────────────
# build_unique_ai() routing
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildUniqueAiRouting:
    @pytest.mark.asyncio
    async def test_build_unique_ai_routes_to_claude__when_claude_agent_config_set(
        self,
    ) -> None:
        """build_unique_ai() returns a ClaudeAgentRunner when claude_agent_config is not None."""
        mock_event = MagicMock()
        mock_event.payload.mcp_servers = []
        mock_logger = MagicMock()
        mock_debug = MagicMock()

        mock_runner = MagicMock(spec=ClaudeAgentRunner)

        with (
            patch(
                "unique_orchestrator.unique_ai_builder._build_common",
                return_value=MagicMock(),
            ),
            patch(
                "unique_orchestrator.unique_ai_builder._build_claude_agent",
                return_value=mock_runner,
            ) as mock_build_claude,
        ):
            from unique_orchestrator.unique_ai_builder import build_unique_ai

            # Use plain MagicMock (not spec=UniqueAIConfig): Pydantic v2 models define
            # fields via __pydantic_fields__ rather than class-level attributes, so
            # spec= won't find 'agent' and raises AttributeError on nested access.
            config = MagicMock()
            config.agent.experimental.claude_agent_config = ClaudeAgentConfig()
            config.agent.experimental.responses_api_config.use_responses_api = False

            result = await build_unique_ai(
                event=mock_event,
                logger=mock_logger,
                config=config,
                debug_info_manager=mock_debug,
            )

        mock_build_claude.assert_called_once()
        assert result is mock_runner

    @pytest.mark.asyncio
    async def test_build_unique_ai_does_not_route_to_claude__when_claude_agent_config_none(
        self,
    ) -> None:
        """Existing completions routing is unchanged when claude_agent_config is None."""
        mock_event = MagicMock()
        mock_event.payload.mcp_servers = []
        mock_logger = MagicMock()
        mock_debug = MagicMock()

        mock_completions_runner = MagicMock()

        with (
            patch(
                "unique_orchestrator.unique_ai_builder._build_common",
                return_value=MagicMock(),
            ),
            patch(
                "unique_orchestrator.unique_ai_builder._build_claude_agent",
            ) as mock_build_claude,
            patch(
                "unique_orchestrator.unique_ai_builder._build_completions",
                return_value=mock_completions_runner,
            ) as mock_build_completions,
        ):
            from unique_orchestrator.unique_ai_builder import build_unique_ai

            config = MagicMock()
            config.agent.experimental.claude_agent_config = None
            config.agent.experimental.responses_api_config.use_responses_api = False

            result = await build_unique_ai(
                event=mock_event,
                logger=mock_logger,
                config=config,
                debug_info_manager=mock_debug,
            )

        mock_build_claude.assert_not_called()
        mock_build_completions.assert_called_once()
        assert result is mock_completions_runner

    @pytest.mark.asyncio
    async def test_build_unique_ai_claude_takes_priority_over_responses_api__when_both_set(
        self,
    ) -> None:
        """Claude Agent config takes priority over responses_api_config when both are set.

        This prevents an edge case where admin accidentally enables both. The Claude
        Agent SDK route is checked first and should always win.
        """
        mock_event = MagicMock()
        mock_event.payload.mcp_servers = []
        mock_logger = MagicMock()
        mock_debug = MagicMock()

        mock_runner = MagicMock(spec=ClaudeAgentRunner)

        with (
            patch(
                "unique_orchestrator.unique_ai_builder._build_common",
                return_value=MagicMock(),
            ),
            patch(
                "unique_orchestrator.unique_ai_builder._build_claude_agent",
                return_value=mock_runner,
            ) as mock_build_claude,
            patch(
                "unique_orchestrator.unique_ai_builder._build_responses",
            ) as mock_build_responses,
        ):
            from unique_orchestrator.unique_ai_builder import build_unique_ai

            config = MagicMock()
            config.agent.experimental.claude_agent_config = ClaudeAgentConfig()
            # responses_api also set — Claude should still win
            config.agent.experimental.responses_api_config.use_responses_api = True

            result = await build_unique_ai(
                event=mock_event,
                logger=mock_logger,
                config=config,
                debug_info_manager=mock_debug,
            )

        mock_build_claude.assert_called_once()
        mock_build_responses.assert_not_called()
        assert result is mock_runner
