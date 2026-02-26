import pytest
from pydantic import ValidationError
from unique_toolkit._common.utils.jinja.utils import validate_template_placeholders
from unique_toolkit.language_model.default_language_model import DEFAULT_GPT_4o
from unique_toolkit.language_model.infos import LanguageModelInfo

from unique_follow_up_questions.config import FollowUpQuestionsConfig
from unique_follow_up_questions.schema import FollowUpCategory, FollowUpQuestion


@pytest.fixture
def valid_config():
    return FollowUpQuestionsConfig()


def test_default_config_values(valid_config):
    """Test that default values are set correctly."""
    assert valid_config.language_model.name == DEFAULT_GPT_4o
    assert valid_config.number_of_questions == 3
    assert valid_config.adapt_to_language is True
    assert isinstance(valid_config.examples, list)
    assert len(valid_config.examples) > 0
    assert all(isinstance(q, FollowUpQuestion) for q in valid_config.examples)


def test_use_structured_output_property(valid_config):
    """Test the use_structured_output property."""
    # Test with default model (GPT-4o) which supports structured output
    assert valid_config.use_structured_output is True

    # Test that the property checks for STRUCTURED_OUTPUT capability
    config_with_gpt4o = FollowUpQuestionsConfig(
        language_model=LanguageModelInfo.from_name(
            DEFAULT_GPT_4o,
        )
    )
    # GPT-4o now supports structured output
    assert config_with_gpt4o.use_structured_output is True


def test_validate_user_prompt():
    """Test the user prompt validation."""
    # Test with valid prompt containing all required placeholders
    valid_prompt = "Conversation history: {{conversation_history}} "
    config = FollowUpQuestionsConfig(user_prompt=valid_prompt)
    assert config.user_prompt == valid_prompt

    # Test with invalid prompt missing required placeholder
    invalid_prompt = "No placeholders here"
    config = FollowUpQuestionsConfig(user_prompt=invalid_prompt)
    # Should fall back to default template
    assert config.user_prompt != invalid_prompt


def test_validate_system_prompt():
    """Test the system prompt validation."""
    # Test with valid prompt containing all required placeholders
    valid_prompt = """
    Number of questions: {{number_of_questions}}
    Examples: {{examples}}
    Example category: {{example.category}}
    Example question: {{example.question}}
    Output schema: {{output_schema}}
    """
    config = FollowUpQuestionsConfig(system_prompt=valid_prompt)
    assert config.system_prompt == valid_prompt

    # Test with invalid prompt missing required placeholder
    invalid_prompt = "Missing required placeholders"
    config = FollowUpQuestionsConfig(system_prompt=invalid_prompt)
    # Should fall back to default template
    assert config.system_prompt != invalid_prompt


def test_validate_suggestions_format():
    """Test the suggestions format validation."""
    # Test with valid format containing all required placeholders
    valid_format = """
    Questions: {{questions}}
    Question: {{question.question}}
    Encoded URI: {{question.encoded_uri}}
    """
    config = FollowUpQuestionsConfig(suggestions_format=valid_format)
    assert config.suggestions_format == valid_format

    # Test with invalid format missing required placeholder
    invalid_format = "Missing required placeholders"
    config = FollowUpQuestionsConfig(suggestions_format=invalid_format)
    # Should fall back to default template
    assert config.suggestions_format != invalid_format


def test_custom_config_values():
    """Test setting custom configuration values."""
    custom_examples = [
        FollowUpQuestion(
            category=FollowUpCategory.CLARIFICATION,
            question="Custom question 1",
        ),
        FollowUpQuestion(
            category=FollowUpCategory.ELABORATION, question="Custom question 2"
        ),
    ]

    config = FollowUpQuestionsConfig(
        number_of_questions=5,
        adapt_to_language=False,
        examples=custom_examples,
    )

    assert config.number_of_questions == 5
    assert config.adapt_to_language is False
    assert config.examples == custom_examples


def test_invalid_config_values():
    """Test that invalid configuration values raise appropriate errors."""
    # Test invalid number_of_questions
    with pytest.raises(ValidationError):
        FollowUpQuestionsConfig(number_of_questions=-1)

    # Test invalid examples
    with pytest.raises(ValidationError):
        FollowUpQuestionsConfig(
            examples=[
                FollowUpQuestion(
                    category="Inexistent Category",  # type: ignore
                    question="not a FollowUpQuestion",
                )
            ]
        )


def test_template_validation_integration():
    """Test integration with template validation utilities."""
    config = FollowUpQuestionsConfig()

    # Test user prompt validation
    user_validation = validate_template_placeholders(
        config.user_prompt,
        required_placeholders={"conversation_history"},
        optional_placeholders={"additional_context", "language"},
    )
    assert user_validation.is_valid

    # Test system prompt validation
    system_validation = validate_template_placeholders(
        config.system_prompt,
        required_placeholders={
            "number_of_questions",
            "examples",
            "example.category",
            "example.question",
            "output_schema",
        },
        optional_placeholders={"loop.index", "loop"},
    )
    assert system_validation.is_valid

    # Test suggestions format validation
    suggestions_validation = validate_template_placeholders(
        config.suggestions_format,
        required_placeholders={
            "questions",
            "question.question",
            "question.encoded_uri",
        },
        optional_placeholders=set(),
    )
    assert suggestions_validation.is_valid
