import re

from unique_toolkit.agentic.history_manager.history_manager import HistoryManager
from unique_toolkit.agentic.postprocessor.postprocessor_manager import Postprocessor
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.language_model.builder import MessagesBuilder
from unique_toolkit.language_model.schemas import (
    LanguageModelMessage,
    LanguageModelMessages,
    LanguageModelStreamResponse,
)
from unique_toolkit.language_model.service import LanguageModelService
from unique_toolkit.language_model.utils import convert_string_to_json

from unique_follow_up_questions.config import FollowUpQuestionsConfig
from unique_follow_up_questions.prompts.params import (
    FollowUpQuestionResponseParams,
    FollowUpQuestionSystemPromptParams,
    FollowUpQuestionUserPromptParams,
)
from unique_follow_up_questions.schema import FollowUpQuestionsOutput


class FollowUpPostprocessor(Postprocessor):
    """
    Postprocessor for follow-up questions in the loop agent.
    This class handles the processing of follow-up questions based on the
    provided configuration and the results of the evaluation checks.
    """

    def __init__(
        self,
        logger,
        config: FollowUpQuestionsConfig,
        event: ChatEvent,
        historyManager: HistoryManager,
        llm_service: LanguageModelService,
    ):
        super().__init__(name="FollowUpQuestionPostprocessor")
        self._logger = logger
        self._config = config
        self._language = event.payload.user_message.language
        self._historyManager = historyManager
        self._llm_service = llm_service

    async def run(self, loop_response: LanguageModelStreamResponse) -> None:
        history = await self._historyManager.get_user_visible_chat_history(
            loop_response.message.text,
            self.remove_from_text,
        )

        # TODO: Include history as separate messages and not as part of the user message. This allows to include images again for follow-up questions.
        self._remove_image_urls_from_history(history)

        self._text = await self._get_follow_up_question_suggestion(
            language=self._language,
            language_model_service=self._llm_service,
            history=history.root,
        )

    def apply_postprocessing_to_response(
        self, loop_response: LanguageModelStreamResponse
    ) -> bool:
        if not self._text or len(self._text) == 0:
            return False

        # Append the follow-up question suggestions to the loop response
        loop_response.message.text += "\n\n" + self._text
        return True

    async def remove_from_text(self, text: str) -> str:
        return re.sub(
            r"<follow-up-question>.*?</follow-up-question>",
            "",
            text,
            flags=re.DOTALL,
        )

    def _remove_image_urls_from_history(self, history: LanguageModelMessages) -> None:
        """
        Remove image_url content from message history.
        
        Args:
            history: The message history to clean
        """
        for message in history.root:
            if message.role != "user" and message.content:
                # Check if message.content is a list and remove dictionaries with 'type': 'image_url'
                if isinstance(message.content, list):
                    message.content = [
                        item for item in message.content 
                        if not (isinstance(item, dict) and item.get('type') == 'image_url')
                    ]

    async def _get_follow_up_question_suggestion(
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
        self._logger.info("Start get_follow_up_question_suggestion")

        system_prompt = FollowUpQuestionSystemPromptParams(
            examples=self._config.examples,
            number_of_questions=self._config.number_of_questions,
        ).render_template(self._config.system_prompt)

        user_prompt = FollowUpQuestionUserPromptParams(
            conversation_history=history,
            additional_context=additional_context,
            language=language if self._config.adapt_to_language else None,
        ).render_template(self._config.user_prompt)

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
        ).render_template(self._config.suggestions_format)

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
            if self._config.use_structured_output:
                response = language_model_service.complete(
                    messages=messages,
                    model_name=self._config.language_model.name,
                    structured_output_model=FollowUpQuestionsOutput,
                )
                parsed_content = response.choices[0].message.parsed
            else:
                response = language_model_service.complete(
                    messages=messages,
                    model_name=self._config.language_model.name,
                )
                content = response.choices[0].message.content
                if not isinstance(content, str):
                    raise ValueError("Language model response content must be a string")
                parsed_content = convert_string_to_json(content)

            return FollowUpQuestionsOutput.model_validate(parsed_content)

        except Exception as e:
            self._logger.error(
                f"Failed to generate follow-up questions: {str(e)}",
                exc_info=True,
            )
            return FollowUpQuestionsOutput()
