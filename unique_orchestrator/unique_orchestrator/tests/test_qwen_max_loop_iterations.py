"""
Tests for Qwen-specific max loop iterations configuration.

This module tests the QwenConfig.max_loop_iterations field, the ClipInt validation
on UniqueAIAgentConfig.max_loop_iterations, and the _effective_max_loop_iterations
property in UniqueAI.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from unique_orchestrator.config import (
    LIMIT_MAX_LOOP_ITERATIONS,
    QwenConfig,
    UniqueAIAgentConfig,
    UniqueAIConfig,
)

if TYPE_CHECKING:
    from unique_orchestrator.unique_ai import UniqueAI


class TestQwenConfigMaxLoopIterations:
    """Test suite for QwenConfig.max_loop_iterations field validation."""

    @pytest.mark.ai
    def test_qwen_config__max_loop_iterations__accepts_valid_value(self) -> None:
        """
        Purpose: Verify QwenConfig accepts valid max_loop_iterations within range.
        Why this matters: Ensures custom iteration limits can be set for Qwen models.
        Setup summary: Instantiate QwenConfig with valid value, assert value is preserved.
        """
        # Arrange
        valid_iterations: int = 5

        # Act
        config: QwenConfig = QwenConfig(max_loop_iterations=valid_iterations)

        # Assert
        assert config.max_loop_iterations == valid_iterations

    @pytest.mark.ai
    def test_qwen_config__max_loop_iterations__clips_value_above_maximum(self) -> None:
        """
        Purpose: Verify ClipInt validation clips values exceeding the maximum limit.
        Why this matters: Prevents excessive loop iterations that could cause performance issues.
        Setup summary: Provide value above LIMIT_MAX_LOOP_ITERATIONS, assert clipped to maximum.
        """
        # Arrange
        value_above_max: int = LIMIT_MAX_LOOP_ITERATIONS + 10

        # Act
        config: QwenConfig = QwenConfig(max_loop_iterations=value_above_max)

        # Assert
        assert config.max_loop_iterations == LIMIT_MAX_LOOP_ITERATIONS

    @pytest.mark.ai
    def test_qwen_config__max_loop_iterations__clips_value_below_minimum(self) -> None:
        """
        Purpose: Verify ClipInt validation clips values below the minimum limit (1).
        Why this matters: Ensures at least one iteration can occur.
        Setup summary: Provide value below 1, assert clipped to minimum.
        """
        # Arrange
        value_below_min: int = 0

        # Act
        config: QwenConfig = QwenConfig(max_loop_iterations=value_below_min)

        # Assert
        assert config.max_loop_iterations == 1

    @pytest.mark.ai
    def test_qwen_config__max_loop_iterations__accepts_boundary_values(self) -> None:
        """
        Purpose: Verify ClipInt accepts both min (1) and max boundary values.
        Why this matters: Ensures boundary conditions work correctly for edge cases.
        Setup summary: Test with min and max boundary values, assert values preserved.
        """
        # Arrange & Act
        config_min: QwenConfig = QwenConfig(max_loop_iterations=1)
        config_max: QwenConfig = QwenConfig(
            max_loop_iterations=LIMIT_MAX_LOOP_ITERATIONS
        )

        # Assert
        assert config_min.max_loop_iterations == 1
        assert config_max.max_loop_iterations == LIMIT_MAX_LOOP_ITERATIONS


class TestUniqueAIAgentConfigMaxLoopIterations:
    """Test suite for UniqueAIAgentConfig.max_loop_iterations field validation."""

    @pytest.mark.ai
    def test_agent_config__max_loop_iterations__clips_value_above_maximum(self) -> None:
        """
        Purpose: Verify ClipInt validation clips values exceeding the maximum limit.
        Why this matters: Prevents excessive loop iterations for general models.
        Setup summary: Provide value above LIMIT_MAX_LOOP_ITERATIONS, assert clipped to maximum.
        """
        # Arrange
        value_above_max: int = 100

        # Act
        config: UniqueAIAgentConfig = UniqueAIAgentConfig(
            max_loop_iterations=value_above_max
        )

        # Assert
        assert config.max_loop_iterations == LIMIT_MAX_LOOP_ITERATIONS

    @pytest.mark.ai
    def test_agent_config__max_loop_iterations__clips_value_below_minimum(self) -> None:
        """
        Purpose: Verify ClipInt validation clips values below the minimum limit (1).
        Why this matters: Ensures at least one iteration can occur for all models.
        Setup summary: Provide value below 1, assert clipped to minimum.
        """
        # Arrange
        value_below_min: int = -5

        # Act
        config: UniqueAIAgentConfig = UniqueAIAgentConfig(
            max_loop_iterations=value_below_min
        )

        # Assert
        assert config.max_loop_iterations == 1


class TestEffectiveMaxLoopIterations:
    """Test suite for UniqueAI._effective_max_loop_iterations property."""

    @pytest.fixture
    def mock_unique_ai_with_config(self, monkeypatch: pytest.MonkeyPatch) -> "UniqueAI":
        """Create a UniqueAI instance with real config and mocked dependencies."""
        # Mock MessageStepLogger module before importing UniqueAI
        mock_service_module = MagicMock()
        mock_service_module.MessageStepLogger = MagicMock()
        monkeypatch.setitem(
            sys.modules,
            "unique_toolkit.agentic.message_log_manager.service",
            mock_service_module,
        )

        from unique_orchestrator.unique_ai import UniqueAI

        # Create minimal event structure
        dummy_event = MagicMock()
        dummy_event.payload.assistant_message.id = "test-assistant-id"

        # Use REAL config so nested attribute access works correctly
        config: UniqueAIConfig = UniqueAIConfig()

        ua = UniqueAI(
            logger=MagicMock(),
            event=dummy_event,
            config=config,
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
        return ua

    @pytest.mark.ai
    def test_effective_max_loop_iterations__returns_qwen_value__for_qwen_model(
        self,
        mock_unique_ai_with_config: "UniqueAI",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify _effective_max_loop_iterations returns Qwen-specific value for Qwen models.
        Why this matters: Qwen models require different iteration limits than other models.
        Setup summary: Mock is_qwen_model to return True, verify Qwen config value is used.
        """
        # Arrange
        monkeypatch.setattr(
            "unique_orchestrator.unique_ai.is_qwen_model",
            lambda model: True,
        )
        qwen_max_iterations: int = 3
        mock_unique_ai_with_config._config.agent.experimental.loop_configuration.model_specific.qwen.max_loop_iterations = qwen_max_iterations
        mock_unique_ai_with_config._config.agent.max_loop_iterations = 8

        # Act
        result: int = mock_unique_ai_with_config._effective_max_loop_iterations

        # Assert
        assert result == qwen_max_iterations

    @pytest.mark.ai
    def test_effective_max_loop_iterations__returns_agent_value__for_non_qwen_model(
        self,
        mock_unique_ai_with_config: "UniqueAI",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify _effective_max_loop_iterations returns agent config value for non-Qwen models.
        Why this matters: Non-Qwen models should use the standard agent configuration.
        Setup summary: Mock is_qwen_model to return False, verify agent config value is used.
        """
        # Arrange
        monkeypatch.setattr(
            "unique_orchestrator.unique_ai.is_qwen_model",
            lambda model: False,
        )
        agent_max_iterations: int = 7
        mock_unique_ai_with_config._config.agent.max_loop_iterations = (
            agent_max_iterations
        )
        mock_unique_ai_with_config._config.agent.experimental.loop_configuration.model_specific.qwen.max_loop_iterations = 3

        # Act
        result: int = mock_unique_ai_with_config._effective_max_loop_iterations

        # Assert
        assert result == agent_max_iterations

    @pytest.mark.ai
    def test_effective_max_loop_iterations__uses_correct_language_model__for_check(
        self,
        mock_unique_ai_with_config: "UniqueAI",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify _effective_max_loop_iterations passes the correct language model to is_qwen_model.
        Why this matters: Model type detection must use the configured language model.
        Setup summary: Mock is_qwen_model, call property, assert called with correct model.
        """
        # Arrange
        captured_model = None

        def capture_is_qwen_model(model):
            nonlocal captured_model
            captured_model = model
            return False

        monkeypatch.setattr(
            "unique_orchestrator.unique_ai.is_qwen_model",
            capture_is_qwen_model,
        )
        expected_model = mock_unique_ai_with_config._config.space.language_model

        # Act
        _ = mock_unique_ai_with_config._effective_max_loop_iterations

        # Assert
        assert captured_model is expected_model
