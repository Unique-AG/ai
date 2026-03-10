"""
Tests for Qwen-specific max loop iterations configuration.

This module tests the QwenConfig.max_loop_iterations field, the ClipInt validation
on UniqueAIAgentConfig.max_loop_iterations, and the max_loop_iterations
property on UniqueAIConfig.
"""

from __future__ import annotations

import pytest

from unique_orchestrator.config import (
    LIMIT_MAX_LOOP_ITERATIONS,
    QwenConfig,
    UniqueAIAgentConfig,
    UniqueAIConfig,
)


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


class TestConfigMaxLoopIterations:
    """Test suite for UniqueAIConfig.max_loop_iterations property."""

    @pytest.mark.ai
    def test_max_loop_iterations__returns_qwen_value__for_qwen_model(self) -> None:
        """
        Purpose: Verify max_loop_iterations returns Qwen-specific value for Qwen models.
        Why this matters: Qwen models require different iteration limits than other models.
        """
        config: UniqueAIConfig = UniqueAIConfig()
        config.space.language_model = "litellm/qwen3"
        qwen_max_iterations: int = 3
        config.agent.experimental.loop_configuration.model_specific.qwen.max_loop_iterations = qwen_max_iterations
        config.agent.max_loop_iterations = 8

        assert config.max_loop_iterations == qwen_max_iterations

    @pytest.mark.ai
    def test_max_loop_iterations__returns_agent_value__for_non_qwen_model(self) -> None:
        """
        Purpose: Verify max_loop_iterations returns agent config value for non-Qwen models.
        Why this matters: Non-Qwen models should use the standard agent configuration.
        """
        config: UniqueAIConfig = UniqueAIConfig()
        config.space.language_model = "gpt-4o"
        agent_max_iterations: int = 7
        config.agent.max_loop_iterations = agent_max_iterations
        config.agent.experimental.loop_configuration.model_specific.qwen.max_loop_iterations = 3

        assert config.max_loop_iterations == agent_max_iterations
