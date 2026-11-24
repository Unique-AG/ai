"""Tests for evaluation factories passed to the Unique AI builder."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from unique_toolkit.agentic.evaluation.evaluation_manager import (
    Evaluation,
    EvaluationManager,
)
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName

from unique_orchestrator.config import UniqueAIConfig
from unique_orchestrator.unique_ai_builder import (
    EvaluationBuildContext,
    EvaluationFactory,
    _build_common,
)

MODULE = "unique_orchestrator.unique_ai_builder"


class _BuiltInHallucinationEvaluation(Evaluation):
    def __init__(self, *args: object) -> None:
        super().__init__(EvaluationMetricName.HALLUCINATION)


class _SuppliedEvaluation(Evaluation):
    pass


@pytest.fixture
def chat_service() -> MagicMock:
    service = MagicMock()
    service.download_chat_images_and_documents_async = AsyncMock(return_value=([], []))
    return service


@pytest.fixture
def reference_manager() -> MagicMock:
    return MagicMock()


@pytest.fixture(autouse=True)
def _patch_constructors(
    monkeypatch: pytest.MonkeyPatch,
    chat_service: MagicMock,
    reference_manager: MagicMock,
) -> None:
    monkeypatch.setattr(f"{MODULE}.ChatService", lambda event: chat_service)
    monkeypatch.setattr(
        f"{MODULE}.LanguageModelService.from_event", lambda event: MagicMock()
    )
    monkeypatch.setattr(
        f"{MODULE}.ContentService.from_event", lambda event: MagicMock()
    )
    monkeypatch.setattr(f"{MODULE}.SubAgentResponseWatcher", MagicMock)
    monkeypatch.setattr(f"{MODULE}.ToolProgressReporter", lambda **kw: MagicMock())
    monkeypatch.setattr(f"{MODULE}.ThinkingManager", lambda **kw: MagicMock())
    monkeypatch.setattr(f"{MODULE}.ReferenceManager", lambda: reference_manager)
    monkeypatch.setattr(
        f"{MODULE}.HallucinationEvaluation", _BuiltInHallucinationEvaluation
    )
    monkeypatch.setattr(f"{MODULE}.MCPManager", lambda **kw: MagicMock())
    monkeypatch.setattr(f"{MODULE}.A2AManager", lambda **kw: MagicMock())
    monkeypatch.setattr(f"{MODULE}.PostprocessorManager", lambda **kw: MagicMock())
    monkeypatch.setattr(f"{MODULE}.MessageStepLogger", lambda *a: MagicMock())


def _make_event() -> MagicMock:
    event = MagicMock()
    event.payload.mcp_servers = []
    event.payload.additional_parameters = None
    return event


async def _build_evaluation_manager(
    evaluation_factories: list[EvaluationFactory],
) -> EvaluationManager:
    components = await _build_common(
        _make_event(),
        MagicMock(),
        UniqueAIConfig(),
        evaluation_factories=evaluation_factories,
    )
    return components.evaluation_manager


@pytest.mark.ai
async def test_build_common__registers_built_in_hallucination_check__without_factories() -> (
    None
):
    """
    Purpose: Verify the builder is unchanged when no factory is passed.
    Why this matters: Callers that do not use the hook keep the built-in check.
    Setup summary: Build with no factories; assert the built-in check is registered.
    """
    evaluation_manager = await _build_evaluation_manager([])

    assert isinstance(
        evaluation_manager.get_evaluation_by_name(EvaluationMetricName.HALLUCINATION),
        _BuiltInHallucinationEvaluation,
    )


@pytest.mark.ai
async def test_build_common__adds_factory_evaluation__next_to_built_in_check() -> None:
    """
    Purpose: Verify a factory evaluation with a new name is added.
    Why this matters: A caller can add an evaluation without losing the built-in check.
    Setup summary: Build with a factory for a new name; assert both are registered.
    """
    supplied = _SuppliedEvaluation(EvaluationMetricName.CONTEXT_RELEVANCY)

    evaluation_manager = await _build_evaluation_manager([lambda context: supplied])

    assert (
        evaluation_manager.get_evaluation_by_name(
            EvaluationMetricName.CONTEXT_RELEVANCY
        )
        is supplied
    )
    assert isinstance(
        evaluation_manager.get_evaluation_by_name(EvaluationMetricName.HALLUCINATION),
        _BuiltInHallucinationEvaluation,
    )


@pytest.mark.ai
async def test_build_common__replaces_built_in_hallucination_check__without_creating_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify a factory evaluation named HALLUCINATION replaces the built-in check.
    Why this matters: The built-in check must not be created, so only one check runs.
    Setup summary: Build with a HALLUCINATION factory; assert it is registered and the
    built-in constructor is never called.
    """
    built_in_constructor = MagicMock()
    monkeypatch.setattr(f"{MODULE}.HallucinationEvaluation", built_in_constructor)
    supplied = _SuppliedEvaluation(EvaluationMetricName.HALLUCINATION)

    evaluation_manager = await _build_evaluation_manager([lambda context: supplied])

    assert (
        evaluation_manager.get_evaluation_by_name(EvaluationMetricName.HALLUCINATION)
        is supplied
    )
    built_in_constructor.assert_not_called()


@pytest.mark.ai
async def test_build_common__passes_turn_components__to_factory(
    chat_service: MagicMock,
    reference_manager: MagicMock,
) -> None:
    """
    Purpose: Verify the factory receives the turn's chat service and reference manager.
    Why this matters: The evaluation must read the same references the answer cites.
    Setup summary: Build with a recording factory; assert the context it received.
    """
    received: list[EvaluationBuildContext] = []

    def build(context: EvaluationBuildContext) -> Evaluation:
        received.append(context)
        return _SuppliedEvaluation(EvaluationMetricName.HALLUCINATION)

    await _build_evaluation_manager([build])

    assert received == [
        EvaluationBuildContext(
            chat_service=chat_service, reference_manager=reference_manager
        )
    ]
