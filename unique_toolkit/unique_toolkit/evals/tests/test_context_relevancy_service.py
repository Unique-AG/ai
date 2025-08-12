from unittest.mock import MagicMock, patch

import pytest
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.service import LanguageModelName
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelCompletionChoice,
    LanguageModelMessages,
)
from unique_toolkit.language_model.service import LanguageModelResponse
from unique_toolkit.evals.config import EvaluationMetricConfig
from unique_toolkit.evals.context_relevancy.prompts import (
    CONTEXT_RELEVANCY_METRIC_SYSTEM_MSG,
)
from unique_toolkit.evals.context_relevancy.schema import (
    EvaluationSchemaStructuredOutput,
)
from unique_toolkit.evals.context_relevancy.service import (
    ContextRelevancyEvaluator,
)
from unique_toolkit.evals.exception import EvaluatorException
from unique_toolkit.evals.schemas import (
    EvaluationMetricInput,
    EvaluationMetricName,
    EvaluationMetricResult,
)


@pytest.fixture
def event():
    event = MagicMock(spec=ChatEvent)
    event.payload = MagicMock()
    event.payload.user_message = MagicMock()
    event.payload.user_message.text = "Test query"
    event.user_id = "user_0"
    event.company_id = "company_0"
    return event


@pytest.fixture
def evaluator(event):
    return ContextRelevancyEvaluator(event)


@pytest.fixture
def basic_config():
    return EvaluationMetricConfig(
        enabled=True,
        name=EvaluationMetricName.CONTEXT_RELEVANCY,
        language_model=LanguageModelInfo.from_name(
            LanguageModelName.AZURE_GPT_4o_2024_0806
        ),
    )


@pytest.fixture
def structured_config(basic_config):
    model_info = LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_4o_2024_0806)
    return EvaluationMetricConfig(
        enabled=True,
        name=EvaluationMetricName.CONTEXT_RELEVANCY,
        language_model=model_info,
    )


@pytest.fixture
def sample_input():
    return EvaluationMetricInput(
        input_text="test query",
        context_texts=["test context 1", "test context 2"],
    )


@pytest.mark.asyncio
async def test_analyze_disabled(evaluator, sample_input, basic_config):
    basic_config.enabled = False
    result = await evaluator.analyze(sample_input, basic_config)
    assert result is None


@pytest.mark.asyncio
async def test_analyze_empty_context(evaluator, basic_config):
    input_with_empty_context = EvaluationMetricInput(
        input_text="test query", context_texts=[]
    )

    with pytest.raises(EvaluatorException) as exc_info:
        await evaluator.analyze(input_with_empty_context, basic_config)

    assert "No context texts provided." in str(exc_info.value)


@pytest.mark.asyncio
async def test_analyze_regular_output(evaluator, sample_input, basic_config):
    mock_result = LanguageModelResponse(
        choices=[
            LanguageModelCompletionChoice(
                index=0,
                message=LanguageModelAssistantMessage(
                    content="""{
                        "value": "high",
                        "reason": "Test reason"
                    }"""
                ),
                finish_reason="stop",
            )
        ]
    )

    with patch.object(
        evaluator.language_model_service,
        "complete_async",
        return_value=mock_result,
    ) as mock_complete:
        result = await evaluator.analyze(sample_input, basic_config)

        assert isinstance(result, EvaluationMetricResult)
        assert result.value.lower() == "high"
        mock_complete.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_structured_output(evaluator, sample_input, structured_config):
    mock_result = LanguageModelResponse(
        choices=[
            LanguageModelCompletionChoice(
                index=0,
                message=LanguageModelAssistantMessage(
                    content="HIGH",
                    parsed={"value": "high", "reason": "Test reason"},
                ),
                finish_reason="stop",
            )
        ]
    )

    structured_output_schema = EvaluationSchemaStructuredOutput

    with patch.object(
        evaluator.language_model_service,
        "complete_async",
        return_value=mock_result,
    ) as mock_complete:
        result = await evaluator.analyze(
            sample_input, structured_config, structured_output_schema
        )
        assert isinstance(result, EvaluationMetricResult)
        assert result.value.lower() == "high"
        mock_complete.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_structured_output_validation_error(
    evaluator, sample_input, structured_config
):
    mock_result = LanguageModelResponse(
        choices=[
            LanguageModelCompletionChoice(
                index=0,
                message=LanguageModelAssistantMessage(
                    content="HIGH", parsed={"invalid": "data"}
                ),
                finish_reason="stop",
            )
        ]
    )

    structured_output_schema = EvaluationSchemaStructuredOutput

    with patch.object(
        evaluator.language_model_service,
        "complete_async",
        return_value=mock_result,
    ):
        with pytest.raises(EvaluatorException) as exc_info:
            await evaluator.analyze(
                sample_input, structured_config, structured_output_schema
            )
        assert "Error occurred during structured output validation" in str(
            exc_info.value
        )


@pytest.mark.asyncio
async def test_analyze_regular_output_empty_response(
    evaluator, sample_input, basic_config
):
    mock_result = LanguageModelResponse(
        choices=[
            LanguageModelCompletionChoice(
                index=0,
                message=LanguageModelAssistantMessage(content=""),
                finish_reason="stop",
            )
        ]
    )

    with patch.object(
        evaluator.language_model_service,
        "complete_async",
        return_value=mock_result,
    ):
        with pytest.raises(EvaluatorException) as exc_info:
            await evaluator.analyze(sample_input, basic_config)
        assert "did not return a result" in str(exc_info.value)


def test_compose_msgs_regular(evaluator, sample_input, basic_config):
    messages = evaluator._compose_msgs(
        sample_input, basic_config, enable_structured_output=False
    )

    assert isinstance(messages, LanguageModelMessages)
    assert messages.root[0].content == CONTEXT_RELEVANCY_METRIC_SYSTEM_MSG
    assert isinstance(messages.root[1].content, str)
    assert "test query" in messages.root[1].content
    assert "test context 1" in messages.root[1].content
    assert "test context 2" in messages.root[1].content


def test_compose_msgs_structured(evaluator, sample_input, structured_config):
    messages = evaluator._compose_msgs(
        sample_input, structured_config, enable_structured_output=True
    )

    assert isinstance(messages, LanguageModelMessages)
    assert len(messages.root) == 2
    assert (
        messages.root[0].content != CONTEXT_RELEVANCY_METRIC_SYSTEM_MSG
    )  # Should use structured output prompt
    assert isinstance(messages.root[1].content, str)
    assert "test query" in messages.root[1].content
    assert "test context 1" in messages.root[1].content
    assert "test context 2" in messages.root[1].content


@pytest.mark.asyncio
async def test_analyze_unknown_error(evaluator, sample_input, basic_config):
    with patch.object(
        evaluator.language_model_service,
        "complete_async",
        side_effect=Exception("Unknown error"),
    ):
        with pytest.raises(EvaluatorException) as exc_info:
            await evaluator.analyze(sample_input, basic_config)
        assert "Unknown error occurred during context relevancy metric analysis" in str(
            exc_info.value
        )
