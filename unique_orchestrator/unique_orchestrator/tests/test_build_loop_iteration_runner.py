"""
Tests for the build_loop_iteration_runner function.

This module tests the factory function that creates the appropriate loop iteration
runner based on configuration settings, including responses API support, Qwen-specific
runners, and planning middleware.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from unique_toolkit.agentic.loop_runner import (
    BasicLoopIterationRunner,
    PlanningConfig,
    PlanningMiddleware,
    QwenLoopIterationRunner,
    ResponsesBasicLoopIterationRunner,
)

from unique_orchestrator._builders.loop_iteration_runner import (
    build_loop_iteration_runner,
)
from unique_orchestrator.config import UniqueAIConfig


class TestBuildLoopIterationRunnerResponsesApi:
    """Test suite for build_loop_iteration_runner with responses API enabled."""

    @pytest.mark.ai
    def test_build_loop_iteration_runner__returns_responses_runner__when_responses_api_enabled(
        self,
    ) -> None:
        """
        Purpose: Verify function returns ResponsesBasicLoopIterationRunner when use_responses_api=True.
        Why this matters: Responses API requires a different runner implementation.
        Setup summary: Call with use_responses_api=True, assert correct runner type returned.
        """
        # Arrange
        config: UniqueAIConfig = UniqueAIConfig()
        history_manager: MagicMock = MagicMock()
        llm_service: MagicMock = MagicMock()
        chat_service: MagicMock = MagicMock()

        # Act
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=history_manager,
            llm_service=llm_service,
            chat_service=chat_service,
            use_responses_api=True,
        )

        # Assert
        assert isinstance(runner, ResponsesBasicLoopIterationRunner)

    @pytest.mark.ai
    def test_build_loop_iteration_runner__uses_agent_max_iterations__for_responses_runner(
        self,
    ) -> None:
        """
        Purpose: Verify ResponsesBasicLoopIterationRunner uses agent.max_loop_iterations config.
        Why this matters: Ensures correct iteration limit is applied to responses API runner.
        Setup summary: Set custom max_loop_iterations, assert runner config matches.
        """
        # Arrange
        config: UniqueAIConfig = UniqueAIConfig()
        config.agent.max_loop_iterations = 7
        history_manager: MagicMock = MagicMock()
        llm_service: MagicMock = MagicMock()
        chat_service: MagicMock = MagicMock()

        # Act
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=history_manager,
            llm_service=llm_service,
            chat_service=chat_service,
            use_responses_api=True,
        )

        # Assert
        assert isinstance(runner, ResponsesBasicLoopIterationRunner)
        assert runner._config.max_loop_iterations == 7


class TestBuildLoopIterationRunnerCompletionsApi:
    """Test suite for build_loop_iteration_runner with completions API (default)."""

    @pytest.mark.ai
    def test_build_loop_iteration_runner__returns_basic_runner__for_non_qwen_model(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify function returns BasicLoopIterationRunner for non-Qwen models.
        Why this matters: Non-Qwen models use the standard loop iteration runner.
        Setup summary: Mock is_qwen_model to return False, assert BasicLoopIterationRunner returned.
        """
        # Arrange
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.is_qwen_model",
            lambda model: False,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        history_manager: MagicMock = MagicMock()
        llm_service: MagicMock = MagicMock()
        chat_service: MagicMock = MagicMock()

        # Act
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=history_manager,
            llm_service=llm_service,
            chat_service=chat_service,
            use_responses_api=False,
        )

        # Assert
        assert isinstance(runner, BasicLoopIterationRunner)

    @pytest.mark.ai
    def test_build_loop_iteration_runner__uses_agent_max_iterations__for_basic_runner(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify BasicLoopIterationRunner uses agent.max_loop_iterations config.
        Why this matters: Ensures correct iteration limit is applied to basic runner.
        Setup summary: Set custom max_loop_iterations, mock non-Qwen model, assert runner config matches.
        """
        # Arrange
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.is_qwen_model",
            lambda model: False,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        config.agent.max_loop_iterations = 8
        history_manager: MagicMock = MagicMock()
        llm_service: MagicMock = MagicMock()
        chat_service: MagicMock = MagicMock()

        # Act
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=history_manager,
            llm_service=llm_service,
            chat_service=chat_service,
            use_responses_api=False,
        )

        # Assert
        assert isinstance(runner, BasicLoopIterationRunner)
        assert runner._config.max_loop_iterations == 8


class TestBuildLoopIterationRunnerQwenModel:
    """Test suite for build_loop_iteration_runner with Qwen models."""

    @pytest.mark.ai
    def test_build_loop_iteration_runner__returns_qwen_runner__for_qwen_model(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify function returns QwenLoopIterationRunner for Qwen models.
        Why this matters: Qwen models require specific handling for tool calls and iterations.
        Setup summary: Mock is_qwen_model to return True, assert QwenLoopIterationRunner returned.
        """
        # Arrange
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.is_qwen_model",
            lambda model: True,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        history_manager: MagicMock = MagicMock()
        llm_service: MagicMock = MagicMock()
        chat_service: MagicMock = MagicMock()

        # Act
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=history_manager,
            llm_service=llm_service,
            chat_service=chat_service,
            use_responses_api=False,
        )

        # Assert
        assert isinstance(runner, QwenLoopIterationRunner)

    @pytest.mark.ai
    def test_build_loop_iteration_runner__uses_qwen_specific_max_iterations__for_qwen_runner(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify QwenLoopIterationRunner uses Qwen-specific max_loop_iterations, not agent default.
        Why this matters: Qwen models have different optimal iteration limits than other models.
        Setup summary: Set different values for agent and Qwen max_iterations, assert Qwen value is used.
        """
        # Arrange
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.is_qwen_model",
            lambda model: True,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        config.agent.max_loop_iterations = 10
        config.agent.experimental.loop_configuration.model_specific.qwen.max_loop_iterations = 3
        history_manager: MagicMock = MagicMock()
        llm_service: MagicMock = MagicMock()
        chat_service: MagicMock = MagicMock()

        # Act
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=history_manager,
            llm_service=llm_service,
            chat_service=chat_service,
            use_responses_api=False,
        )

        # Assert
        assert isinstance(runner, QwenLoopIterationRunner)
        assert runner._max_loop_iterations == 3

    @pytest.mark.ai
    def test_build_loop_iteration_runner__uses_qwen_forced_tool_instruction__for_qwen_runner(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify QwenLoopIterationRunner uses Qwen-specific forced tool call instruction.
        Why this matters: Qwen models require special prompting for tool calls.
        Setup summary: Set custom forced_tool_call_instruction, assert runner uses it.
        """
        # Arrange
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.is_qwen_model",
            lambda model: True,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        custom_instruction: str = "Custom forced tool instruction for Qwen"
        config.agent.experimental.loop_configuration.model_specific.qwen.forced_tool_call_instruction = custom_instruction
        history_manager: MagicMock = MagicMock()
        llm_service: MagicMock = MagicMock()
        chat_service: MagicMock = MagicMock()

        # Act
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=history_manager,
            llm_service=llm_service,
            chat_service=chat_service,
            use_responses_api=False,
        )

        # Assert
        assert isinstance(runner, QwenLoopIterationRunner)
        assert runner._qwen_forced_tool_call_instruction == custom_instruction

    @pytest.mark.ai
    def test_build_loop_iteration_runner__uses_qwen_last_iteration_instruction__for_qwen_runner(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify QwenLoopIterationRunner uses Qwen-specific last iteration instruction.
        Why this matters: Qwen models need special instructions on final iteration.
        Setup summary: Set custom last_iteration_instruction, assert runner uses it.
        """
        # Arrange
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.is_qwen_model",
            lambda model: True,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        custom_instruction: str = "Custom last iteration instruction for Qwen"
        config.agent.experimental.loop_configuration.model_specific.qwen.last_iteration_instruction = custom_instruction
        history_manager: MagicMock = MagicMock()
        llm_service: MagicMock = MagicMock()
        chat_service: MagicMock = MagicMock()

        # Act
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=history_manager,
            llm_service=llm_service,
            chat_service=chat_service,
            use_responses_api=False,
        )

        # Assert
        assert isinstance(runner, QwenLoopIterationRunner)
        assert runner._qwen_last_iteration_instruction == custom_instruction

    @pytest.mark.ai
    def test_build_loop_iteration_runner__passes_chat_service__to_qwen_runner(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify QwenLoopIterationRunner receives the chat_service dependency.
        Why this matters: Qwen runner needs chat_service to modify assistant messages.
        Setup summary: Pass mock chat_service, assert runner has it.
        """
        # Arrange
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.is_qwen_model",
            lambda model: True,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        history_manager: MagicMock = MagicMock()
        llm_service: MagicMock = MagicMock()
        chat_service: MagicMock = MagicMock()

        # Act
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=history_manager,
            llm_service=llm_service,
            chat_service=chat_service,
            use_responses_api=False,
        )

        # Assert
        assert isinstance(runner, QwenLoopIterationRunner)
        assert runner._chat_service is chat_service


class TestBuildLoopIterationRunnerPlanningMiddleware:
    """Test suite for build_loop_iteration_runner with planning middleware."""

    @pytest.mark.ai
    def test_build_loop_iteration_runner__wraps_with_planning__when_planning_config_set(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify function wraps runner in PlanningMiddleware when planning_config is set.
        Why this matters: Planning middleware adds planning steps before iterations.
        Setup summary: Set planning_config, assert PlanningMiddleware is returned.
        """
        # Arrange
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.is_qwen_model",
            lambda model: False,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        config.agent.experimental.loop_configuration.planning_config = PlanningConfig()
        history_manager: MagicMock = MagicMock()
        llm_service: MagicMock = MagicMock()
        chat_service: MagicMock = MagicMock()

        # Act
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=history_manager,
            llm_service=llm_service,
            chat_service=chat_service,
            use_responses_api=False,
        )

        # Assert
        assert isinstance(runner, PlanningMiddleware)

    @pytest.mark.ai
    def test_build_loop_iteration_runner__wraps_basic_runner__in_planning_middleware(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify PlanningMiddleware wraps BasicLoopIterationRunner for non-Qwen models.
        Why this matters: Inner runner must be correct type for proper delegation.
        Setup summary: Set planning_config for non-Qwen model, assert inner runner is BasicLoopIterationRunner.
        """
        # Arrange
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.is_qwen_model",
            lambda model: False,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        config.agent.experimental.loop_configuration.planning_config = PlanningConfig()
        history_manager: MagicMock = MagicMock()
        llm_service: MagicMock = MagicMock()
        chat_service: MagicMock = MagicMock()

        # Act
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=history_manager,
            llm_service=llm_service,
            chat_service=chat_service,
            use_responses_api=False,
        )

        # Assert
        assert isinstance(runner, PlanningMiddleware)
        assert isinstance(runner._loop_runner, BasicLoopIterationRunner)

    @pytest.mark.ai
    def test_build_loop_iteration_runner__wraps_qwen_runner__in_planning_middleware(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify PlanningMiddleware wraps QwenLoopIterationRunner for Qwen models.
        Why this matters: Qwen-specific behavior must be preserved when planning is enabled.
        Setup summary: Set planning_config for Qwen model, assert inner runner is QwenLoopIterationRunner.
        """
        # Arrange
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.is_qwen_model",
            lambda model: True,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        config.agent.experimental.loop_configuration.planning_config = PlanningConfig()
        history_manager: MagicMock = MagicMock()
        llm_service: MagicMock = MagicMock()
        chat_service: MagicMock = MagicMock()

        # Act
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=history_manager,
            llm_service=llm_service,
            chat_service=chat_service,
            use_responses_api=False,
        )

        # Assert
        assert isinstance(runner, PlanningMiddleware)
        assert isinstance(runner._loop_runner, QwenLoopIterationRunner)

    @pytest.mark.ai
    def test_build_loop_iteration_runner__passes_planning_config__to_middleware(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify PlanningMiddleware receives the correct planning_config.
        Why this matters: Planning behavior depends on configuration settings.
        Setup summary: Create custom PlanningConfig, assert middleware has it.
        """
        # Arrange
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.is_qwen_model",
            lambda model: False,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        planning_config: PlanningConfig = PlanningConfig(
            ignored_options=["custom_option"]
        )
        config.agent.experimental.loop_configuration.planning_config = planning_config
        history_manager: MagicMock = MagicMock()
        llm_service: MagicMock = MagicMock()
        chat_service: MagicMock = MagicMock()

        # Act
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=history_manager,
            llm_service=llm_service,
            chat_service=chat_service,
            use_responses_api=False,
        )

        # Assert
        assert isinstance(runner, PlanningMiddleware)
        assert runner._config is planning_config

    @pytest.mark.ai
    def test_build_loop_iteration_runner__passes_history_manager__to_middleware(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify PlanningMiddleware receives the history_manager dependency.
        Why this matters: Planning middleware needs history context for planning steps.
        Setup summary: Pass mock history_manager, assert middleware has it.
        """
        # Arrange
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.is_qwen_model",
            lambda model: False,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        config.agent.experimental.loop_configuration.planning_config = PlanningConfig()
        history_manager: MagicMock = MagicMock()
        llm_service: MagicMock = MagicMock()
        chat_service: MagicMock = MagicMock()

        # Act
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=history_manager,
            llm_service=llm_service,
            chat_service=chat_service,
            use_responses_api=False,
        )

        # Assert
        assert isinstance(runner, PlanningMiddleware)
        assert runner._history_manager is history_manager

    @pytest.mark.ai
    def test_build_loop_iteration_runner__passes_llm_service__to_middleware(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify PlanningMiddleware receives the llm_service dependency.
        Why this matters: Planning middleware uses LLM service for planning calls.
        Setup summary: Pass mock llm_service, assert middleware has it.
        """
        # Arrange
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.is_qwen_model",
            lambda model: False,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        config.agent.experimental.loop_configuration.planning_config = PlanningConfig()
        history_manager: MagicMock = MagicMock()
        llm_service: MagicMock = MagicMock()
        chat_service: MagicMock = MagicMock()

        # Act
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=history_manager,
            llm_service=llm_service,
            chat_service=chat_service,
            use_responses_api=False,
        )

        # Assert
        assert isinstance(runner, PlanningMiddleware)
        assert runner._llm_service is llm_service

    @pytest.mark.ai
    def test_build_loop_iteration_runner__no_planning__when_planning_config_none(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify no PlanningMiddleware is added when planning_config is None.
        Why this matters: Planning should only be enabled when explicitly configured.
        Setup summary: Leave planning_config as None (default), assert basic runner returned.
        """
        # Arrange
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.is_qwen_model",
            lambda model: False,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        # planning_config is None by default
        history_manager: MagicMock = MagicMock()
        llm_service: MagicMock = MagicMock()
        chat_service: MagicMock = MagicMock()

        # Act
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=history_manager,
            llm_service=llm_service,
            chat_service=chat_service,
            use_responses_api=False,
        )

        # Assert
        assert isinstance(runner, BasicLoopIterationRunner)
        assert not isinstance(runner, PlanningMiddleware)


class TestBuildLoopIterationRunnerModelDetection:
    """Test suite for model detection in build_loop_iteration_runner."""

    @pytest.mark.ai
    def test_build_loop_iteration_runner__checks_correct_language_model__for_qwen_detection(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify is_qwen_model is called with the correct language model from config.
        Why this matters: Model detection must use the configured space language model.
        Setup summary: Capture model passed to is_qwen_model, assert it matches config.
        """
        # Arrange
        captured_model = None

        def capture_is_qwen_model(model):
            nonlocal captured_model
            captured_model = model
            return False

        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.is_qwen_model",
            capture_is_qwen_model,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        expected_model = config.space.language_model
        history_manager: MagicMock = MagicMock()
        llm_service: MagicMock = MagicMock()
        chat_service: MagicMock = MagicMock()

        # Act
        build_loop_iteration_runner(
            config=config,
            history_manager=history_manager,
            llm_service=llm_service,
            chat_service=chat_service,
            use_responses_api=False,
        )

        # Assert
        assert captured_model is expected_model
