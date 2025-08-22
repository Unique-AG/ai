from unittest.mock import MagicMock

import pytest
from unique_toolkit import LanguageModelService
from unique_toolkit.language_model import (
    LanguageModelMessage,
    LanguageModelMessageRole,
)
from unique_toolkit.language_model.infos import LanguageModelInfo

from config import FollowUpQuestionsConfig
from schema import FollowUpCategory, FollowUpQuestion, FollowUpQuestionsOutput
from unique_toolkit._common.default_language_model import DEFAULT_GPT_35_TURBO

from service import FollowUpQuestionService




@pytest.fixture
def config():
    return FollowUpQuestionsConfig(
        examples=[
            FollowUpQuestion(
                category=FollowUpCategory.CLARIFICATION, question="Example 1"
            ),
            FollowUpQuestion(
                category=FollowUpCategory.CLARIFICATION, question="Example 2"
            ),
        ],
        number_of_questions=3,
        system_prompt="System prompt template",
        user_prompt="User prompt template",
        suggestions_format="Suggestions format template",
        adapt_to_language=True,
    )


@pytest.fixture
def config_without_structured_output():
    return FollowUpQuestionsConfig(
        language_model=LanguageModelInfo.from_name(DEFAULT_GPT_35_TURBO),
        examples=[
            FollowUpQuestion(
                category=FollowUpCategory.CLARIFICATION, question="Example 1"
            ),
            FollowUpQuestion(
                category=FollowUpCategory.CLARIFICATION, question="Example 2"
            ),
        ],
        number_of_questions=3,
        system_prompt="System prompt template",
        user_prompt="User prompt template",
        suggestions_format="Suggestions format template",
        adapt_to_language=True,
    )


@pytest.fixture
def language_model_service():
    return MagicMock(spec=LanguageModelService)


@pytest.fixture
def service(config):
    return FollowUpQuestionService(
        config=config,
    )


@pytest.fixture
def service_without_structured_output(
    config_without_structured_output,
):
    return FollowUpQuestionService(
        config=config_without_structured_output,
    )


def test_clean_history():
    # Arrange
    history = [
        LanguageModelMessage(
            role=LanguageModelMessageRole.USER, content="User message"
        ),
        LanguageModelMessage(
            role=LanguageModelMessageRole.ASSISTANT,
            content="""Assistant message with follow-up questions.<follow-up-question> Questions 1, 2, 3 </follow-up-question>""",
        ),
    ]

    # Act
    cleaned_history = FollowUpQuestionService.clean_history(history)

    # Assert
    assert len(cleaned_history) == 2
    assert cleaned_history[0].content == "User message"
    assert (
        cleaned_history[1].content
        == "Assistant message with follow-up questions."
    )


@pytest.mark.asyncio
async def test_get_follow_up_question_suggestion(
    service, config, language_model_service
):
    # Arrange
    history = [
        LanguageModelMessage(
            role=LanguageModelMessageRole.USER, content="User message"
        ),
        LanguageModelMessage(
            role=LanguageModelMessageRole.ASSISTANT,
            content="Assistant message",
        ),
    ]
    language = "en"
    additional_context = "Some context"

    # Mock the language model response
    mock_output = FollowUpQuestionsOutput(
        questions=[
            FollowUpQuestion(
                category=FollowUpCategory.CLARIFICATION, question="Question 1"
            ),
            FollowUpQuestion(
                category=FollowUpCategory.CLARIFICATION, question="Question 2"
            ),
            FollowUpQuestion(
                category=FollowUpCategory.CLARIFICATION, question="Question 3"
            ),
        ]
    )
    language_model_service.complete.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(parsed=mock_output.model_dump()))]
    )

    # Act
    result = await service.get_follow_up_question_suggestion(
        language=language,
        language_model_service=language_model_service,
        history=history,
        additional_context=additional_context,
    )

    # Assert
    assert isinstance(result, str)
    language_model_service.complete.assert_called_once()
    call_args = language_model_service.complete.call_args[1]
    assert call_args["model_name"] == config.language_model.name
    assert call_args["structured_output_model"] == FollowUpQuestionsOutput


@pytest.mark.asyncio
async def test_get_follow_up_question_suggestion_without_structured_output(
    service_without_structured_output,
    config_without_structured_output,
    language_model_service,
):
    # Arrange
    history = [
        LanguageModelMessage(
            role=LanguageModelMessageRole.USER, content="User message"
        )
    ]
    language = "en"

    # Mock the language model response
    mock_content = '{"questions": [{"question": "Question 1"}]}'
    language_model_service.complete.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=mock_content))]
    )

    # Act
    result = await service_without_structured_output.get_follow_up_question_suggestion(
        language=language,
        language_model_service=language_model_service,
        history=history,
    )

    # Assert
    assert isinstance(result, str)
    language_model_service.complete.assert_called_once()
    call_args = language_model_service.complete.call_args[1]
    assert (
        call_args["model_name"]
        == config_without_structured_output.language_model.name
    )
    assert "structured_output_model" not in call_args


@pytest.mark.asyncio
async def test_get_follow_up_question_suggestion_error_handling(
    service, config, language_model_service
):
    # Arrange
    history = [
        LanguageModelMessage(
            role=LanguageModelMessageRole.USER, content="User message"
        )
    ]
    language = "en"

    # Mock the language model to raise an exception
    language_model_service.complete.side_effect = Exception("Test error")

    # Act
    result = await service.get_follow_up_question_suggestion(
        language=language,
        language_model_service=language_model_service,
        history=history,
    )

    # Assert
    assert isinstance(result, str)
    assert result == ""  # Should return empty string on error
