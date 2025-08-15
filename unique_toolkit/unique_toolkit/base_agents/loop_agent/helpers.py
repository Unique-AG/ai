from datetime import datetime
from typing import Callable

from pydantic import BaseModel
from unique_toolkit.chat.schemas import ChatMessage
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.schemas import Content
from unique_toolkit.content.service import ContentService
from unique_toolkit.content.utils import count_tokens
from unique_toolkit.language_model.builder import MessagesBuilder
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessage,
    LanguageModelMessageRole,
    LanguageModelStreamResponse,
)
from unique_toolkit.evaluators.schemas import EvaluationMetricResult


EMPTY_MESSAGE_WARNING = (
    "⚠️ **The language model was unable to produce an output.**\n"
    "It did not generate any content or perform a tool call in response to your request. "
    "This is a limitation of the language model itself.\n\n"
    "**Please try adapting or simplifying your prompt.** "
    "Rewording your input can often help the model respond successfully."
)


class EvaluationCheckResultsPostprocessed(BaseModel):
    history: list[LanguageModelMessage] = []
    passed: bool = True

    @classmethod
    def from_evaluation_results(
        cls, result_evalution_checks: list[EvaluationMetricResult]
    ) -> "EvaluationCheckResultsPostprocessed":
        """
        Postprocess the evaluation check results:
        (1) build up history with evaluation check results. include them as assistant messages.
        (2) set the evaluation result passed flag.

        Returns:
            list[LanguageModelMessage]: The history based on the evaluation results
            bool: The evaluation result passed flag
        """

        evaluation_postprocessed = cls()
        for evaluation_result in result_evalution_checks:
            if not evaluation_result.is_positive:
                evaluation_postprocessed.passed = False
                if evaluation_result.user_info:
                    evaluation_postprocessed.history.append(
                        LanguageModelAssistantMessage(
                            content=evaluation_result.user_info
                        )
                    )
        return evaluation_postprocessed


async def get_history(
    chat_service: ChatService,
    content_service: ContentService,
    max_history_tokens: int,
    postprocessing_step: Callable[
        [list[LanguageModelMessage]], list[LanguageModelMessage]
    ]
    | None = None,
) -> list[LanguageModelMessage]:
    """
    Get the history of the conversation. The function will retrieve a subset of the full history based on the configuration.

    Returns:
        list[LanguageModelMessage]: The history
    """
    # Get uploaded files
    uploaded_files = content_service.search_content_on_chat(
        chat_id=chat_service.chat_id
    )
    # Get all message history
    full_history = await chat_service.get_full_history_async()

    merged_history = merge_history_and_uploads(full_history, uploaded_files)

    if postprocessing_step is not None:
        merged_history = postprocessing_step(merged_history)

    limited_history = limit_to_token_window(merged_history, max_history_tokens)

    return limited_history


def merge_history_and_uploads(
    history: list[ChatMessage], uploads: list[Content]
) -> list[LanguageModelMessage]:
    # Assert that all content have a created_at
    content_with_created_at = [content for content in uploads if content.created_at]
    sorted_history = sorted(
        history + content_with_created_at,
        key=lambda x: x.created_at or datetime.min,
    )

    msg_builder = MessagesBuilder()
    for msg in sorted_history:
        if isinstance(msg, Content):
            msg_builder.user_message_append(
                f"Uploaded file: {msg.key}, ContentId: {msg.id}"
            )
        else:
            msg_builder.messages.append(
                LanguageModelMessage(
                    role=LanguageModelMessageRole(msg.role),
                    content=msg.content,
                )
            )
    return msg_builder.messages


def limit_to_token_window(
    messages: list[LanguageModelMessage], token_limit: int
) -> list[LanguageModelMessage]:
    selected_messages = []
    token_count = 0
    for msg in messages[::-1]:
        msg_token_count = count_tokens(str(msg.content))
        if token_count + msg_token_count > token_limit:
            break
        selected_messages.append(msg)
        token_count += msg_token_count
    return selected_messages[::-1]
