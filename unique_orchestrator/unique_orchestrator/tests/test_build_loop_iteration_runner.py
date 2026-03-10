"""
Tests for the build_loop_iteration_runner function.

This module tests the factory function that creates the appropriate loop iteration
runner based on configuration settings, including responses API support, model-specific
runners (Qwen, Mistral), and planning middleware.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from unique_toolkit.agentic.loop_runner import (
    BasicLoopIterationRunner,
    MistralLoopIterationRunner,
    PlanningConfig,
    PlanningMiddleware,
    QwenLoopIterationRunner,
    ResponsesBasicLoopIterationRunner,
)

from unique_orchestrator._builders.loop_iteration_runner import (
    build_loop_iteration_runner,
)
from unique_orchestrator.config import UniqueAIConfig, get_model_family


class TestGetModelFamily:
    @pytest.mark.ai
    def testget_model_family__returns_qwen__for_qwen_model(self) -> None:
        assert get_model_family("litellm/qwen3") == "qwen"
        assert get_model_family("Qwen-2.5") == "qwen"

    @pytest.mark.ai
    def testget_model_family__returns_mistral__for_mistral_model(self) -> None:
        assert get_model_family("mistral-large-latest") == "mistral"
        assert get_model_family("Mistral-7B") == "mistral"

    @pytest.mark.ai
    def testget_model_family__returns_none__for_other_models(self) -> None:
        assert get_model_family("gpt-4o") is None
        assert get_model_family("claude-3") is None


class TestBuildLoopIterationRunnerResponsesApi:
    @pytest.mark.ai
    def test_build_loop_iteration_runner__returns_responses_runner__when_responses_api_enabled(
        self,
    ) -> None:
        config: UniqueAIConfig = UniqueAIConfig()
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=True,
        )
        assert isinstance(runner, ResponsesBasicLoopIterationRunner)

    @pytest.mark.ai
    def test_build_loop_iteration_runner__uses_agent_max_iterations__for_responses_runner(
        self,
    ) -> None:
        config: UniqueAIConfig = UniqueAIConfig()
        config.agent.max_loop_iterations = 7
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=True,
        )
        assert isinstance(runner, ResponsesBasicLoopIterationRunner)
        assert runner._config.max_loop_iterations == 7


class TestBuildLoopIterationRunnerCompletionsApi:
    @pytest.mark.ai
    def test_build_loop_iteration_runner__returns_basic_runner__for_non_special_model(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.get_model_family",
            lambda model_name: None,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert type(runner) is BasicLoopIterationRunner

    @pytest.mark.ai
    def test_build_loop_iteration_runner__uses_agent_max_iterations__for_basic_runner(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.get_model_family",
            lambda model_name: None,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        config.agent.max_loop_iterations = 8
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert isinstance(runner, BasicLoopIterationRunner)
        assert runner._config.max_loop_iterations == 8


class TestBuildLoopIterationRunnerQwenModel:
    @pytest.mark.ai
    def test_build_loop_iteration_runner__returns_qwen_runner__for_qwen_model(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.get_model_family",
            lambda model_name: "qwen",
        )
        config: UniqueAIConfig = UniqueAIConfig()
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert isinstance(runner, QwenLoopIterationRunner)

    @pytest.mark.ai
    def test_build_loop_iteration_runner__uses_qwen_specific_max_iterations__for_qwen_runner(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.get_model_family",
            lambda model_name: "qwen",
        )
        config: UniqueAIConfig = UniqueAIConfig()
        config.agent.max_loop_iterations = 10
        config.agent.experimental.loop_configuration.model_specific.qwen.max_loop_iterations = 3
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert isinstance(runner, QwenLoopIterationRunner)
        assert runner._config.max_loop_iterations == 3

    @pytest.mark.ai
    def test_build_loop_iteration_runner__uses_qwen_forced_tool_instruction__for_qwen_runner(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.get_model_family",
            lambda model_name: "qwen",
        )
        config: UniqueAIConfig = UniqueAIConfig()
        custom_instruction: str = "Custom forced tool instruction for Qwen"
        config.agent.experimental.loop_configuration.model_specific.qwen.forced_tool_call_instruction = custom_instruction
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert isinstance(runner, QwenLoopIterationRunner)
        assert runner._forced_tool_call_instruction == custom_instruction

    @pytest.mark.ai
    def test_build_loop_iteration_runner__uses_qwen_last_iteration_instruction__for_qwen_runner(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.get_model_family",
            lambda model_name: "qwen",
        )
        config: UniqueAIConfig = UniqueAIConfig()
        custom_instruction: str = "Custom last iteration instruction for Qwen"
        config.agent.experimental.loop_configuration.model_specific.qwen.last_iteration_instruction = custom_instruction
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert isinstance(runner, QwenLoopIterationRunner)
        assert runner._last_iteration_instruction == custom_instruction

    @pytest.mark.ai
    def test_build_loop_iteration_runner__passes_chat_service__to_qwen_runner(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.get_model_family",
            lambda model_name: "qwen",
        )
        config: UniqueAIConfig = UniqueAIConfig()
        chat_service: MagicMock = MagicMock()
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=chat_service,
            use_responses_api=False,
        )
        assert isinstance(runner, QwenLoopIterationRunner)
        assert runner._chat_service is chat_service


class TestBuildLoopIterationRunnerMistralModel:
    @pytest.mark.ai
    def test_build_loop_iteration_runner__returns_mistral_runner__for_mistral_model(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.get_model_family",
            lambda model_name: "mistral",
        )
        config: UniqueAIConfig = UniqueAIConfig()
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert isinstance(runner, MistralLoopIterationRunner)

    @pytest.mark.ai
    def test_build_loop_iteration_runner__uses_agent_max_iterations__for_mistral_runner(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.get_model_family",
            lambda model_name: "mistral",
        )
        config: UniqueAIConfig = UniqueAIConfig()
        config.agent.max_loop_iterations = 6
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert isinstance(runner, MistralLoopIterationRunner)
        assert runner._config.max_loop_iterations == 6


class TestBuildLoopIterationRunnerPlanningMiddleware:
    @pytest.mark.ai
    def test_build_loop_iteration_runner__wraps_with_planning__when_planning_config_set(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.get_model_family",
            lambda model_name: None,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        config.agent.experimental.loop_configuration.planning_config = PlanningConfig()
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert isinstance(runner, PlanningMiddleware)

    @pytest.mark.ai
    def test_build_loop_iteration_runner__wraps_basic_runner__in_planning_middleware(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.get_model_family",
            lambda model_name: None,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        config.agent.experimental.loop_configuration.planning_config = PlanningConfig()
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert isinstance(runner, PlanningMiddleware)
        assert type(runner._loop_runner) is BasicLoopIterationRunner

    @pytest.mark.ai
    def test_build_loop_iteration_runner__wraps_qwen_runner__in_planning_middleware(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.get_model_family",
            lambda model_name: "qwen",
        )
        config: UniqueAIConfig = UniqueAIConfig()
        config.agent.experimental.loop_configuration.planning_config = PlanningConfig()
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert isinstance(runner, PlanningMiddleware)
        assert isinstance(runner._loop_runner, QwenLoopIterationRunner)

    @pytest.mark.ai
    def test_build_loop_iteration_runner__wraps_mistral_runner__in_planning_middleware(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.get_model_family",
            lambda model_name: "mistral",
        )
        config: UniqueAIConfig = UniqueAIConfig()
        config.agent.experimental.loop_configuration.planning_config = PlanningConfig()
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert isinstance(runner, PlanningMiddleware)
        assert isinstance(runner._loop_runner, MistralLoopIterationRunner)

    @pytest.mark.ai
    def test_build_loop_iteration_runner__passes_planning_config__to_middleware(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.get_model_family",
            lambda model_name: None,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        planning_config: PlanningConfig = PlanningConfig(
            ignored_options=["custom_option"]
        )
        config.agent.experimental.loop_configuration.planning_config = planning_config
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert isinstance(runner, PlanningMiddleware)
        assert runner._config is planning_config

    @pytest.mark.ai
    def test_build_loop_iteration_runner__passes_history_manager__to_middleware(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.get_model_family",
            lambda model_name: None,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        config.agent.experimental.loop_configuration.planning_config = PlanningConfig()
        history_manager: MagicMock = MagicMock()
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=history_manager,
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert isinstance(runner, PlanningMiddleware)
        assert runner._history_manager is history_manager

    @pytest.mark.ai
    def test_build_loop_iteration_runner__passes_llm_service__to_middleware(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.get_model_family",
            lambda model_name: None,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        config.agent.experimental.loop_configuration.planning_config = PlanningConfig()
        llm_service: MagicMock = MagicMock()
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=llm_service,
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert isinstance(runner, PlanningMiddleware)
        assert runner._llm_service is llm_service

    @pytest.mark.ai
    def test_build_loop_iteration_runner__no_planning__when_planning_config_none(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_orchestrator._builders.loop_iteration_runner.get_model_family",
            lambda model_name: None,
        )
        config: UniqueAIConfig = UniqueAIConfig()
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert isinstance(runner, BasicLoopIterationRunner)
        assert not isinstance(runner, PlanningMiddleware)


class TestBuildLoopIterationRunnerModelFamilyIntegration:
    """Integration tests using real model name strings — no monkeypatching of get_model_family."""

    @pytest.mark.ai
    def test_build_loop_iteration_runner__returns_basic_runner__for_gpt_model_string(
        self,
    ) -> None:
        config: UniqueAIConfig = UniqueAIConfig()
        config.space.language_model = "gpt-4o"  # type: ignore[assignment]
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert type(runner) is BasicLoopIterationRunner

    @pytest.mark.ai
    def test_build_loop_iteration_runner__returns_mistral_runner__for_mistral_model_string(
        self,
    ) -> None:
        config: UniqueAIConfig = UniqueAIConfig()
        config.space.language_model = "mistral-large"  # type: ignore[assignment]
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert isinstance(runner, MistralLoopIterationRunner)

    @pytest.mark.ai
    def test_build_loop_iteration_runner__returns_qwen_runner__for_qwen_model_string(
        self,
    ) -> None:
        config: UniqueAIConfig = UniqueAIConfig()
        config.space.language_model = "litellm/qwen3"  # type: ignore[assignment]
        runner = build_loop_iteration_runner(
            config=config,
            history_manager=MagicMock(),
            llm_service=MagicMock(),
            chat_service=MagicMock(),
            use_responses_api=False,
        )
        assert isinstance(runner, QwenLoopIterationRunner)
