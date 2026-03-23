from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from unique_orchestrator.config import InputTokenDistributionConfig, UniqueAIConfig
from unique_orchestrator.unique_ai_builder import _build_common


class TestBuildCommonToolCallHistoryWiring:
    """Tests that _build_common wires percent_for_tool_call_history into HistoryManagerConfig."""

    def _make_event(self) -> MagicMock:
        event = MagicMock()
        event.payload.mcp_servers = []
        event.payload.a2a = None
        return event

    @pytest.mark.ai
    def test_build_common__passes_percent_for_tool_call_history_to_history_manager_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: Verify that _build_common reads percent_for_tool_call_history from the
        agent config and forwards it to HistoryManagerConfig.

        Why this matters: If the wiring is missing, the HistoryManager will always receive
        the default 0.0 regardless of what the operator configured, silently disabling
        tool call history reconstruction.

        Setup summary: Build a UniqueAIConfig with percent_for_tool_call_history=0.3;
        patch all service constructors that require real I/O; capture HistoryManagerConfig
        kwargs and assert percent_for_tool_call_history=0.3 was passed.
        """
        config = UniqueAIConfig()
        config.agent.input_token_distribution = InputTokenDistributionConfig(
            percent_for_tool_call_history=0.3
        )

        captured: dict = {}

        import unique_orchestrator.unique_ai_builder as builder_mod

        real_hmc = builder_mod.HistoryManagerConfig

        class CapturingHistoryManagerConfig(real_hmc):
            def __init__(self, **kwargs):
                captured.update(kwargs)
                super().__init__(**kwargs)

        event = self._make_event()

        with (
            patch.object(
                builder_mod, "HistoryManagerConfig", CapturingHistoryManagerConfig
            ),
            patch.object(builder_mod, "ChatService", return_value=MagicMock()),
            patch.object(
                builder_mod, "LanguageModelService", MagicMock(from_event=MagicMock())
            ),
            patch.object(
                builder_mod,
                "ContentService",
                MagicMock(from_event=MagicMock(return_value=MagicMock())),
            ),
            patch.object(builder_mod, "HistoryManager", return_value=MagicMock()),
            patch.object(builder_mod, "EvaluationManager", return_value=MagicMock()),
            patch.object(builder_mod, "MCPManager", return_value=MagicMock()),
            patch.object(builder_mod, "A2AManager", return_value=MagicMock()),
            patch.object(builder_mod, "PostprocessorManager", return_value=MagicMock()),
            patch.object(builder_mod, "MessageStepLogger", return_value=MagicMock()),
            patch.object(builder_mod, "ReferenceManager", return_value=MagicMock()),
            patch.object(
                builder_mod, "SubAgentResponseWatcher", return_value=MagicMock()
            ),
            patch.object(builder_mod, "ThinkingManager", return_value=MagicMock()),
            patch.object(builder_mod, "ToolProgressReporter", return_value=MagicMock()),
            patch.object(builder_mod, "ToolManagerConfig", return_value=MagicMock()),
        ):
            _build_common(event=event, logger=MagicMock(), config=config)

        assert captured.get("percent_for_tool_call_history") == pytest.approx(0.3)

    @pytest.mark.ai
    def test_build_common__passes_zero_percent_for_tool_call_history_by_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: Verify that the default UniqueAIConfig (no explicit tool call budget)
        forwards 0.0 to HistoryManagerConfig, keeping the feature disabled unless
        explicitly configured.

        Why this matters: The default-off behaviour prevents accidental DB overhead for
        deployments that have not opted in to tool call history reconstruction.

        Setup summary: Use an unmodified UniqueAIConfig; capture HistoryManagerConfig
        kwargs and assert percent_for_tool_call_history==0.0.
        """
        config = UniqueAIConfig()

        captured: dict = {}

        import unique_orchestrator.unique_ai_builder as builder_mod

        real_hmc = builder_mod.HistoryManagerConfig

        class CapturingHistoryManagerConfig(real_hmc):
            def __init__(self, **kwargs):
                captured.update(kwargs)
                super().__init__(**kwargs)

        event = self._make_event()

        with (
            patch.object(
                builder_mod, "HistoryManagerConfig", CapturingHistoryManagerConfig
            ),
            patch.object(builder_mod, "ChatService", return_value=MagicMock()),
            patch.object(
                builder_mod, "LanguageModelService", MagicMock(from_event=MagicMock())
            ),
            patch.object(
                builder_mod,
                "ContentService",
                MagicMock(from_event=MagicMock(return_value=MagicMock())),
            ),
            patch.object(builder_mod, "HistoryManager", return_value=MagicMock()),
            patch.object(builder_mod, "EvaluationManager", return_value=MagicMock()),
            patch.object(builder_mod, "MCPManager", return_value=MagicMock()),
            patch.object(builder_mod, "A2AManager", return_value=MagicMock()),
            patch.object(builder_mod, "PostprocessorManager", return_value=MagicMock()),
            patch.object(builder_mod, "MessageStepLogger", return_value=MagicMock()),
            patch.object(builder_mod, "ReferenceManager", return_value=MagicMock()),
            patch.object(
                builder_mod, "SubAgentResponseWatcher", return_value=MagicMock()
            ),
            patch.object(builder_mod, "ThinkingManager", return_value=MagicMock()),
            patch.object(builder_mod, "ToolProgressReporter", return_value=MagicMock()),
            patch.object(builder_mod, "ToolManagerConfig", return_value=MagicMock()),
        ):
            _build_common(event=event, logger=MagicMock(), config=config)

        assert captured.get("percent_for_tool_call_history") == pytest.approx(0.0)
