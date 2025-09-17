from logging import getLogger

from pydantic import BaseModel, Field, field_validator
from unique_toolkit._common.default_language_model import (
    DEFAULT_GPT_4o_STRUCTURED_OUTPUT,
)
from unique_toolkit._common.validators import LMI
from unique_toolkit.language_model.infos import LanguageModelInfo, ModelCapabilities
from unique_toolkit.agentic.tools.config import get_configuration_dict

from unique_follow_up_questions.prompts.params import (
    FOLLOW_UP_QUESTION_SYSTEM_PROMPT_TEMPLATE,
    FOLLOW_UP_QUESTION_USER_PROMPT_TEMPLATE,
    SUGGESTION_FORMAT_TEMPLATE,
)
from unique_follow_up_questions.schema import FollowUpQuestion
from unique_follow_up_questions.utils.jinja.utils import validate_template_placeholders

logger = getLogger(__name__)


class FollowUpQuestionsConfig(BaseModel):
    model_config = get_configuration_dict()
    language_model: LMI = Field(
        default=LanguageModelInfo.from_name(DEFAULT_GPT_4o_STRUCTURED_OUTPUT),
        description="The language model to be used for the follow-up question.",
    )

    user_prompt: str = Field(
        default=FOLLOW_UP_QUESTION_USER_PROMPT_TEMPLATE,
        description="The user prompt to be used for the follow-up question.",
    )
    system_prompt: str = Field(
        default=FOLLOW_UP_QUESTION_SYSTEM_PROMPT_TEMPLATE,
        description="The system prompt to be used for the follow-up question.",
    )
    suggestions_format: str = Field(
        default=SUGGESTION_FORMAT_TEMPLATE,
        description="The suggestion format to be used for displaying the suggestions of follow-up questions.",
    )
    examples: list[FollowUpQuestion] = Field(
        default=FollowUpQuestion.examples(),
        description="The examples to be used for the follow-up question.",
    )
    number_of_questions: int = Field(
        ge=0,
        default=3,
        description="The number of questions to be used for the follow-up question.",
    )
    adapt_to_language: bool = Field(
        default=True,
        description="Whether to adapt the follow-up questions to the language of the conversation.",
    )

    @property
    def use_structured_output(self) -> bool:
        return ModelCapabilities.STRUCTURED_OUTPUT in self.language_model.capabilities

    @field_validator("user_prompt")
    def validate_user_prompt(cls, v: str) -> str:
        required_placeholders = {
            "conversation_history",
        }
        optional_placeholders = {
            "additional_context",
            "language",
        }
        validation_result = validate_template_placeholders(
            v, required_placeholders, optional_placeholders
        )
        if not validation_result.is_valid:
            logger.warning(
                f"User prompt is invalid. "
                f"Missing placeholders: {validation_result.missing_placeholders}, "
                f"unexpected placeholders: {validation_result.unexpected_placeholders}"
            )
            return FOLLOW_UP_QUESTION_USER_PROMPT_TEMPLATE

        logger.info("User prompt is valid.")
        return v

    @field_validator("system_prompt")
    def validate_system_prompt(cls, v: str) -> str:
        required_placeholders = {
            "number_of_questions",
            "examples",
            "example.category",
            "example.question",
            "output_schema",
        }
        optional_placeholders = {
            "loop.index",
            "loop",
        }
        validation_result = validate_template_placeholders(
            v, required_placeholders, optional_placeholders
        )
        if not validation_result.is_valid:
            logger.warning(
                f"System prompt is invalid. "
                f"Missing placeholders: {validation_result.missing_placeholders}, "
                f"unexpected placeholders: {validation_result.unexpected_placeholders}"
            )
            return FOLLOW_UP_QUESTION_SYSTEM_PROMPT_TEMPLATE

        logger.info("System prompt is valid.")
        return v

    @field_validator("suggestions_format")
    def validate_suggestions_format(cls, v: str) -> str:
        required_placeholders = {
            "questions",
            "question.question",
            "question.encoded_uri",
        }
        optional_placeholders = set()
        validation_result = validate_template_placeholders(
            v, required_placeholders, optional_placeholders
        )
        if not validation_result.is_valid:
            logger.warning(
                f"Suggestions format is invalid. "
                f"Missing placeholders: {validation_result.missing_placeholders}, "
                f"unexpected placeholders: {validation_result.unexpected_placeholders}"
            )
            return SUGGESTION_FORMAT_TEMPLATE

        logger.info("Suggestions format is valid.")
        return v
