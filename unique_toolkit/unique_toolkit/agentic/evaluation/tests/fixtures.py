"""Centralized fixtures for evaluation tests."""

from unittest.mock import MagicMock

import pytest

from unique_toolkit.agentic.evaluation.config import EvaluationMetricConfig
from unique_toolkit.agentic.evaluation.context_relevancy.service import (
    ContextRelevancyEvaluator,
)
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationMetricInput,
    EvaluationMetricName,
)
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.service import LanguageModelName
from unique_toolkit.language_model.infos import LanguageModelInfo


@pytest.fixture
def base_chat_event() -> MagicMock:
    """
    Create a base chat event mock for evaluation tests.

    Returns:
        MagicMock configured with standard test event properties.
    """
    event = MagicMock(spec=ChatEvent)
    event.payload = MagicMock()
    event.payload.user_message = MagicMock()
    event.payload.user_message.text = "Test query"
    event.user_id = "user_0"
    event.company_id = "company_0"
    return event


@pytest.fixture
def context_relevancy_evaluator(
    base_chat_event: MagicMock,
) -> ContextRelevancyEvaluator:
    """
    Create a ContextRelevancyEvaluator instance with base event.

    Args:
        base_chat_event: Mock chat event fixture.

    Returns:
        Configured ContextRelevancyEvaluator instance.
    """
    return ContextRelevancyEvaluator(base_chat_event)


@pytest.fixture
def basic_evaluation_config() -> EvaluationMetricConfig:
    """
    Create a basic evaluation config for context relevancy tests.

    Returns:
        EvaluationMetricConfig with standard settings.
    """
    return EvaluationMetricConfig(
        enabled=True,
        name=EvaluationMetricName.CONTEXT_RELEVANCY,
        language_model=LanguageModelInfo.from_name(
            LanguageModelName.AZURE_GPT_4o_2024_0806
        ),
    )


@pytest.fixture
def structured_evaluation_config(
    basic_evaluation_config: EvaluationMetricConfig,
) -> EvaluationMetricConfig:
    """
    Create evaluation config with structured output enabled.

    Args:
        basic_evaluation_config: Base config fixture.

    Returns:
        EvaluationMetricConfig configured for structured output.
    """
    model_info = LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_4o_2024_0806)
    return EvaluationMetricConfig(
        enabled=True,
        name=EvaluationMetricName.CONTEXT_RELEVANCY,
        language_model=model_info,
    )


@pytest.fixture
def sample_evaluation_input() -> EvaluationMetricInput:
    """
    Create sample evaluation input with test data.

    Returns:
        EvaluationMetricInput with test query and contexts.
    """
    return EvaluationMetricInput(
        input_text="test query",
        context_texts=["test context 1", "test context 2"],
    )
