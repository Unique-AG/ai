import logging
import re

from unique_toolkit.language_model import (
    LanguageModelMessage,
    convert_string_to_json,
)
from unique_toolkit.language_model.builder import MessagesBuilder
from unique_toolkit.language_model.schemas import LanguageModelMessages
from unique_toolkit.language_model.service import LanguageModelService

from unique_follow_up_questions.config import FollowUpQuestionsConfig
from unique_follow_up_questions.prompts.params import (
    FollowUpQuestionResponseParams,
    FollowUpQuestionSystemPromptParams,
    FollowUpQuestionUserPromptParams,
)
from unique_follow_up_questions.schema import FollowUpQuestionsOutput

logger = logging.getLogger(__name__)


class FollowUpQuestionService:
    """
    Service for generating follow-up question suggestions based on conversation history.
    """

    def __init__(
        self,
        config: FollowUpQuestionsConfig,
    ):
        """
        Initialize the follow-up question service.

        Args:
            config: Configuration for the follow-up question service
            language_model_service: Service for interacting with language models
        """
        self.config = config

    @staticmethod
    def clean_history(
        history: list[LanguageModelMessage],
    ) -> list[LanguageModelMessage]:
        """
        Remove follow-up question tags from assistant messages in conversation history.

        Args:
            history: List of chat messages to clean
        """

        for message in history:
            if message.role == "assistant" and isinstance(message.content, str):
                # Remove any suggested follow-up questions from the message content
                message.content = re.sub(
                    r"<follow-up-question>.*?</follow-up-question>",
                    "",
                    message.content,
                    flags=re.DOTALL,
                )
        return history

    async def get_follow_up_question_suggestion(
        self,
        language: str,
        language_model_service: LanguageModelService,
        history: list[LanguageModelMessage],
        additional_context: str | None = None,
    ) -> str:
        """
        Generate and format follow-up question suggestions based on conversation history.

        Args:
            language: Language to generate the follow-up questions in
            language_model_service: Service for interacting with the language model
            history: List of previous chat messages in the conversation
            additional_context: Optional extra context to inform question generation
        Returns:
            str: Formatted string containing the suggested follow-up questions

        The function follows these steps:
        1. Cleans the conversation history
        2. Builds system and user prompts
        3. Generates follow-up questions using the language model
        4. Formats the questions according to configured template
        """
        logger.info("Start get_follow_up_question_suggestion")

        history = self.clean_history(history)

        system_prompt = FollowUpQuestionSystemPromptParams(
            examples=self.config.examples,
            number_of_questions=self.config.number_of_questions,
        ).render_template(self.config.system_prompt)

        user_prompt = FollowUpQuestionUserPromptParams(
            conversation_history=history,
            additional_context=additional_context,
            language=language if self.config.adapt_to_language else None,
        ).render_template(self.config.user_prompt)

        messages = (
            MessagesBuilder()
            .system_message_append(system_prompt)
            .user_message_append(user_prompt)
            .build()
        )

        follow_up_questions = await self._generate_follow_up_questions(
            language_model_service,
            messages,
        )

        formatted_suggestions = FollowUpQuestionResponseParams(
            questions=[q.question for q in follow_up_questions.questions],
        ).render_template(self.config.suggestions_format)

        return formatted_suggestions

    async def _generate_follow_up_questions(
        self,
        language_model_service: LanguageModelService,
        messages: LanguageModelMessages,
    ) -> FollowUpQuestionsOutput:
        """
        Generate follow-up questions using the language model.

        Args:
            language_model_service: The language model service to use
            messages: The messages to send to the language model

        Returns:
            FollowUpQuestionsOutput: The generated follow-up questions

        Raises:
            ValueError: If the response from the language model is invalid
        """
        try:
            if self.config.use_structured_output:
                response = language_model_service.complete(
                    messages=messages,
                    model_name=self.config.language_model.name,
                    structured_output_model=FollowUpQuestionsOutput,
                )
                parsed_content = response.choices[0].message.parsed
            else:
                response = language_model_service.complete(
                    messages=messages,
                    model_name=self.config.language_model.name,
                )
                content = response.choices[0].message.content
                if not isinstance(content, str):
                    raise ValueError("Language model response content must be a string")
                parsed_content = convert_string_to_json(content)

            return FollowUpQuestionsOutput.model_validate(parsed_content)

        except Exception as e:
            logger.error(
                f"Failed to generate follow-up questions: {str(e)}",
                exc_info=True,
            )
            return FollowUpQuestionsOutput()
