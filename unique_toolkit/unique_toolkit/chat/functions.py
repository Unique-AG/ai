import logging
import re
from typing import Any, NamedTuple, Sequence

import unique_sdk
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.responses import (
    ResponseIncludable,
    ResponseInputItemParam,
    ResponseInputParam,
    ResponseTextConfigParam,
    ToolParam,
    response_create_params,
)
from openai.types.shared_params import Metadata, Reasoning
from typing_extensions import deprecated
from unique_sdk._list_object import ListObject

from unique_toolkit._common import _time_utils
from unique_toolkit.chat.constants import (
    DEFAULT_MAX_MESSAGES,
)
from unique_toolkit.chat.schemas import (
    ChatMessage,
    ChatMessageAssessment,
    ChatMessageAssessmentLabel,
    ChatMessageAssessmentStatus,
    ChatMessageAssessmentType,
    ChatMessageRole,
    MessageExecution,
    MessageExecutionType,
    MessageExecutionUpdateStatus,
    MessageLog,
    MessageLogDetails,
    MessageLogStatus,
    MessageLogUncitedReferences,
)
from unique_toolkit.content.schemas import ContentChunk, ContentReference
from unique_toolkit.content.utils import count_tokens
from unique_toolkit.language_model.constants import (
    DEFAULT_COMPLETE_TEMPERATURE,
    DEFAULT_COMPLETE_TIMEOUT,
)
from unique_toolkit.language_model.functions import (
    SearchContext,
    _clamp_temperature,
    _prepare_all_completions_params_util,
    _to_search_context,
)
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelName,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessage,
    LanguageModelMessageOptions,
    LanguageModelMessages,
    LanguageModelStreamResponse,
    LanguageModelTool,
    LanguageModelToolDescription,
    ResponsesLanguageModelStreamResponse,
)

logger = logging.getLogger(__name__)


def modify_message(
    user_id: str,
    company_id: str,
    assistant_message_id: str,
    chat_id: str,
    user_message_id: str,
    user_message_text: str,
    assistant: bool,
    content: str | None = None,
    original_content: str | None = None,
    references: list[ContentReference] | None = None,
    debug_info: dict | None = None,
    message_id: str | None = None,
    set_completed_at: bool = False,
) -> ChatMessage:
    """Modifies a chat message synchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        assistant_message_id (str): The assistant message ID.
        chat_id (str): The chat ID.
        user_message_id (str): The user message ID.
        user_message_text (str): The user message text.
        assistant (bool): Whether the message is an assistant message.
        content (str, optional): The new content for the message.
        original_content (str, optional): The original content for the message.
        message_id (str, optional): The message ID. Defaults to None, then the ChatState assistant message id is used.
        references (list[ContentReference]): list of ContentReference objects. Defaults to None.
        debug_info (dict[str, Any]], optional): Debug information. Defaults to None.
        set_completed_at (bool, optional): Whether to set the completedAt field with the current date time. Defaults to False.

    Returns:
        ChatMessage: The modified message.

    Raises:
        Exception: If the modification fails.

    """
    try:
        params = _construct_message_modify_params(
            user_id=user_id,
            company_id=company_id,
            assistant_message_id=assistant_message_id,
            chat_id=chat_id,
            user_message_id=user_message_id,
            user_message_text=user_message_text,
            assistant=assistant,
            content=content,
            original_content=original_content,
            references=references,
            debug_info=debug_info,
            message_id=message_id,
            set_completed_at=set_completed_at,
        )
        message = unique_sdk.Message.modify(**params)
        return ChatMessage(**message)
    except Exception as e:
        logger.error(f"Failed to modify user message: {e}")
        raise e


async def modify_message_async(
    user_id: str,
    company_id: str,
    assistant_message_id: str,
    chat_id: str,
    user_message_id: str,
    user_message_text: str,
    assistant: bool,
    content: str | None = None,
    original_content: str | None = None,
    references: list[ContentReference] | None = None,
    debug_info: dict | None = None,
    message_id: str | None = None,
    set_completed_at: bool = False,
) -> ChatMessage:
    """Modifies a chat message asynchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        assistant_message_id (str): The assistant message ID.
        chat_id (str): The chat ID.
        user_message_id (str): The user message ID.
        user_message_text (str): The user message text.
        assistant (bool): Whether the message is an assistant message.
        content (str, optional): The new content for the message.
        original_content (str, optional): The original content for the message.
        message_id (str, optional): The message ID. Defaults to None, then the ChatState assistant message id is used.
        references (list[ContentReference]): list of ContentReference objects. Defaults to None.
        debug_info (dict[str, Any]], optional): Debug information. Defaults to None.
        set_completed_at (bool, optional): Whether to set the completedAt field with the current date time. Defaults to False.

    Returns:
        ChatMessage: The modified message.

    Raises:
        Exception: If the modification fails.

    """
    try:
        params = _construct_message_modify_params(
            user_id=user_id,
            company_id=company_id,
            assistant_message_id=assistant_message_id,
            chat_id=chat_id,
            user_message_id=user_message_id,
            user_message_text=user_message_text,
            assistant=assistant,
            content=content,
            original_content=original_content,
            references=references,
            debug_info=debug_info,
            message_id=message_id,
            set_completed_at=set_completed_at,
        )
        message = await unique_sdk.Message.modify_async(**params)
        return ChatMessage(**message)
    except Exception as e:
        logger.error(f"Failed to modify user message: {e}")
        raise e


def map_references(references: list[ContentReference]) -> list[dict[str, Any]]:
    return [
        {
            "name": ref.name,
            "url": ref.url,
            "sequenceNumber": ref.sequence_number,
            "sourceId": ref.source_id,
            "source": ref.source,
        }
        for ref in references
    ]


def map_references_with_original_index(
    references: list[ContentReference],
) -> list[dict[str, Any]]:
    """Maps ContentReference objects to dict format for MessageLog API (complete format).

    This function includes all fields including originalIndex for APIs that support it.
    """
    return [
        {
            "name": ref.name,
            "url": ref.url,
            "sequenceNumber": ref.sequence_number,
            "sourceId": ref.source_id,
            "source": ref.source,
            "originalIndex": ref.original_index,
        }
        for ref in references
    ]


def _construct_message_modify_params(
    user_id: str,
    company_id: str,
    assistant_message_id: str,
    chat_id: str,
    user_message_id: str,
    user_message_text: str,
    assistant: bool = True,
    content: str | None = None,
    original_content: str | None = None,
    references: list[ContentReference] | None = None,
    debug_info: dict | None = None,
    message_id: str | None = None,
    set_completed_at: bool = False,
) -> dict[str, Any]:
    completed_at_datetime = None

    if message_id:
        # Message ID specified. No need to guess
        message_id = message_id
    elif assistant:
        # Assistant message ID
        message_id = assistant_message_id
    else:
        message_id = user_message_id
        if content is None:
            content = user_message_text

    if set_completed_at:
        completed_at_datetime = _time_utils.get_datetime_now()

    params = {
        "user_id": user_id,
        "company_id": company_id,
        "id": message_id,
        "chatId": chat_id,
        "text": content,
        "originalText": original_content,
        "references": map_references(references) if references else [],
        "debugInfo": debug_info,
        "completedAt": completed_at_datetime,
    }
    return params


def create_message(
    user_id: str,
    company_id: str,
    chat_id: str,
    assistant_id: str,
    role: ChatMessageRole,
    content: str | None = None,
    original_content: str | None = None,
    references: list[ContentReference] | None = None,
    debug_info: dict | None = None,
    set_completed_at: bool | None = False,
):
    """Creates a message in the chat session synchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        chat_id (str): The chat ID.
        assistant_id (str): The assistant ID.
        role (ChatMessageRole): The role of the message.
        content (str, optional): The content for the message. Defaults to None.
        original_content (str, optional): The original content for the message. Defaults to None.
        references (list[ContentReference], optional): list of ContentReference objects. Defaults to None.
        debug_info (dict[str, Any]], optional): Debug information. Defaults to None.
        set_completed_at (Optional[bool]): Whether to set the completedAt field with the current date time. Defaults to False.

    Returns:
        ChatMessage: The created message.

    Raises:
        Exception: If the creation fails.

    """
    if original_content is None:
        original_content = content

    try:
        params = _construct_message_create_params(
            user_id=user_id,
            company_id=company_id,
            chat_id=chat_id,
            assistant_id=assistant_id,
            role=role,
            content=content,
            original_content=original_content,
            references=references,
            debug_info=debug_info,
            set_completed_at=set_completed_at,
        )

        message = unique_sdk.Message.create(**params)
        return ChatMessage(**message)
    except Exception as e:
        logger.error(f"Failed to create assistant message: {e}")
        raise e


async def create_message_async(
    user_id: str,
    company_id: str,
    chat_id: str,
    assistant_id: str,
    role: ChatMessageRole,
    content: str | None = None,
    original_content: str | None = None,
    references: list[ContentReference] | None = None,
    debug_info: dict | None = None,
    set_completed_at: bool | None = False,
):
    """Creates a message in the chat session synchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        chat_id (str): The chat ID.
        assistant_id (str): The assistant ID.
        role (ChatMessageRole): The role of the message.
        content (str, optional): The content for the message. Defaults to None.
        original_content (str, optional): The original content for the message. Defaults to None.
        references (list[ContentReference], optional): list of ContentReference objects. Defaults to None.
        debug_info (dict[str, Any]], optional): Debug information. Defaults to None.
        set_completed_at (Optional[bool]): Whether to set the completedAt field with the current date time. Defaults to False.

    Returns:
        ChatMessage: The created message.

    Raises:
        Exception: If the creation fails.

    """
    if original_content is None:
        original_content = content

    try:
        params = _construct_message_create_params(
            user_id=user_id,
            company_id=company_id,
            chat_id=chat_id,
            assistant_id=assistant_id,
            role=role,
            content=content,
            original_content=original_content,
            references=references,
            debug_info=debug_info,
            set_completed_at=set_completed_at,
        )

        message = await unique_sdk.Message.create_async(**params)
        return ChatMessage(**message)
    except Exception as e:
        logger.error(f"Failed to create assistant message: {e}")
        raise e


def _construct_message_create_params(
    user_id: str,
    company_id: str,
    chat_id: str,
    assistant_id: str,
    role: ChatMessageRole,
    content: str | None = None,
    original_content: str | None = None,
    references: list[ContentReference] | None = None,
    debug_info: dict | None = None,
    set_completed_at: bool | None = False,
) -> dict[str, Any]:
    if original_content is None:
        original_content = content

    return {
        "user_id": user_id,
        "company_id": company_id,
        "assistantId": assistant_id,
        "role": role.value.upper(),
        "chatId": chat_id,
        "text": content,
        "originalText": original_content,
        "references": map_references(references) if references else [],
        "debugInfo": debug_info or {},
        "completedAt": _time_utils.get_datetime_now() if set_completed_at else None,
    }


def get_selection_from_history(
    full_history: list[ChatMessage],
    max_tokens: int,
    max_messages=DEFAULT_MAX_MESSAGES,
) -> list[ChatMessage]:
    messages = full_history[-max_messages:]
    filtered_messages = [m for m in messages if m.content]
    mapped_messages = []

    for m in filtered_messages:
        m.content = re.sub(r"<sup>\d+</sup>", "", m.content or "")
        m.role = (
            ChatMessageRole.ASSISTANT
            if m.role == ChatMessageRole.ASSISTANT
            else ChatMessageRole.USER
        )
        mapped_messages.append(m)

    return pick_messages_in_reverse_for_token_window(
        messages=mapped_messages,
        limit=max_tokens,
    )


def map_to_chat_messages(messages: list[dict]) -> list[ChatMessage]:
    return [ChatMessage(**msg) for msg in messages]


def pick_messages_in_reverse_for_token_window(
    messages: list[ChatMessage],
    limit: int,
) -> list[ChatMessage]:
    if len(messages) < 1 or limit < 1:
        return []

    last_index = len(messages) - 1
    token_count = count_tokens(messages[last_index].content or "")
    while token_count > limit:
        logger.debug(
            f"Limit too low for the initial message. Last message TokenCount {token_count} available tokens {limit} - cutting message in half until it fits",
        )
        content = messages[last_index].content or ""
        messages[last_index].content = content[: len(content) // 2] + "..."
        token_count = count_tokens(messages[last_index].content or "")

    while token_count <= limit and last_index > 0:
        token_count = count_tokens(
            "".join([msg.content or "" for msg in messages[:last_index]]),
        )
        if token_count <= limit:
            last_index -= 1

    last_index = max(0, last_index)
    return messages[last_index:]


def list_messages(
    event_user_id: str,
    event_company_id: str,
    chat_id: str,
) -> ListObject[unique_sdk.Message]:
    try:
        messages = unique_sdk.Message.list(
            user_id=event_user_id,
            company_id=event_company_id,
            chatId=chat_id,
        )
        return messages
    except Exception as e:
        logger.error(f"Failed to list chat history: {e}")
        raise e


async def list_messages_async(
    event_user_id: str,
    event_company_id: str,
    chat_id: str,
) -> ListObject[unique_sdk.Message]:
    try:
        messages = await unique_sdk.Message.list_async(
            user_id=event_user_id,
            company_id=event_company_id,
            chatId=chat_id,
        )
        return messages
    except Exception as e:
        logger.error(f"Failed to list chat history: {e}")
        raise e


def get_full_history(
    event_user_id: str,
    event_company_id: str,
    event_payload_chat_id: str,
) -> list[ChatMessage]:
    messages = list_messages(event_user_id, event_company_id, event_payload_chat_id)
    messages = filter_valid_messages(messages)

    return map_to_chat_messages(messages)


async def get_full_history_async(
    event_user_id: str,
    event_company_id: str,
    event_payload_chat_id: str,
) -> list[ChatMessage]:
    messages = await list_messages_async(
        event_user_id,
        event_company_id,
        event_payload_chat_id,
    )
    messages = filter_valid_messages(messages)

    return map_to_chat_messages(messages)


def filter_valid_messages(
    messages: ListObject[unique_sdk.Message],
) -> list[dict[str, Any]]:
    SYSTEM_MESSAGE_PREFIX = "[SYSTEM] "

    # Remove the last two messages
    messages = messages["data"][:-2]  # type: ignore
    filtered_messages = []
    for message in messages:
        if message["text"] is None or SYSTEM_MESSAGE_PREFIX in message["text"]:
            continue
        filtered_messages.append(message)

    return filtered_messages


def create_message_assessment(
    user_id: str,
    company_id: str,
    assistant_message_id: str,
    status: ChatMessageAssessmentStatus,
    type: ChatMessageAssessmentType,
    title: str | None = None,
    explanation: str | None = None,
    label: ChatMessageAssessmentLabel | None = None,
    is_visible: bool = True,
) -> ChatMessageAssessment:
    """Creates a message assessment for an assistant message synchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        assistant_message_id (str): The ID of the assistant message to assess
        status (ChatMessageAssessmentStatus): The status of the assessment (e.g. "DONE")
        type (ChatMessageAssessmentType): The type of assessment (e.g. "HALLUCINATION")
        title (str | None): The title of the assessment
        explanation (str | None): Explanation of the assessment
        label (ChatMessageAssessmentLabel | None): The assessment label (e.g. "NEGATIVE")
        is_visible (bool): Whether the assessment is visible to users. Defaults to True.

    Returns:
        ChatMessageAssessment: The created message assessment

    Raises:
        Exception: If the creation fails

    """
    try:
        assessment = unique_sdk.MessageAssessment.create(
            user_id=user_id,
            company_id=company_id,
            messageId=assistant_message_id,
            status=status.name,
            explanation=explanation,
            label=label.name if label else None,
            title=title,
            type=type.name,
            isVisible=is_visible,
        )
        return ChatMessageAssessment(**assessment)
    except Exception as e:
        logger.error(f"Failed to create message assessment: {e}")
        raise e


async def create_message_assessment_async(
    user_id: str,
    company_id: str,
    assistant_message_id: str,
    status: ChatMessageAssessmentStatus,
    type: ChatMessageAssessmentType,
    title: str | None = None,
    explanation: str | None = None,
    label: ChatMessageAssessmentLabel | None = None,
    is_visible: bool = True,
) -> ChatMessageAssessment:
    """Creates a message assessment for an assistant message asynchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        assistant_message_id (str): The ID of the assistant message to assess
        status (ChatMessageAssessmentStatus): The status of the assessment (e.g. "DONE")
        type (ChatMessageAssessmentType): The type of assessment (e.g. "HALLUCINATION")
        title (str | None): The title of the assessment
        explanation (str | None): Explanation of the assessment
        label (ChatMessageAssessmentLabel | None): The assessment label (e.g. "NEGATIVE")
        is_visible (bool): Whether the assessment is visible to users. Defaults to True.

    Returns:
        MessageAssessment: The created message assessment

    Raises:
        Exception: If the creation fails

    """
    try:
        assessment = await unique_sdk.MessageAssessment.create_async(
            user_id=user_id,
            company_id=company_id,
            messageId=assistant_message_id,
            status=status.name,
            explanation=explanation,
            label=label.name if label else None,
            title=title,
            type=type.name,
            isVisible=is_visible,
        )
        return ChatMessageAssessment(**assessment)
    except Exception as e:
        logger.error(f"Failed to create message assessment: {e}")
        raise e


def modify_message_assessment(
    user_id: str,
    company_id: str,
    assistant_message_id: str,
    status: ChatMessageAssessmentStatus,
    type: ChatMessageAssessmentType,
    title: str | None = None,
    explanation: str | None = None,
    label: ChatMessageAssessmentLabel | None = None,
) -> ChatMessageAssessment:
    """Modifies a message assessment for an assistant message synchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        assistant_message_id (str): The ID of the assistant message to assess
        status (MessageAssessmentStatus): The status of the assessment (e.g. "DONE")
        title (str | None): The title of the assessment
        explanation (str | None): Explanation of the assessment
        label (ChatMessageAssessmentLabel | None): The assessment label (e.g. "NEGATIVE")
        type (ChatMessageAssessmentType): The type of assessment (e.g. "HALLUCINATION")

    Returns:
        dict: The modified message assessment

    Raises:
        Exception: If the modification fails

    """
    try:
        assessment = unique_sdk.MessageAssessment.modify(
            user_id=user_id,
            company_id=company_id,
            messageId=assistant_message_id,
            status=status.name,
            title=title,
            explanation=explanation,
            label=label.name if label else None,
            type=type.name,
        )
        return ChatMessageAssessment(**assessment)
    except Exception as e:
        logger.error(f"Failed to modify message assessment: {e}")
        raise e


async def modify_message_assessment_async(
    user_id: str,
    company_id: str,
    assistant_message_id: str,
    type: ChatMessageAssessmentType,
    title: str | None = None,
    status: ChatMessageAssessmentStatus | None = None,
    explanation: str | None = None,
    label: ChatMessageAssessmentLabel | None = None,
) -> ChatMessageAssessment:
    """Modifies a message assessment for an assistant message asynchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        assistant_message_id (str): The ID of the assistant message to assess
        type (MessageAssessmentType): The type of assessment (e.g. "HALLUCINATION")
        title (str | None): The title of the assessment
        status (MessageAssessmentStatus): The status of the assessment (e.g. "DONE")
        explanation (str | None): Explanation of the assessment
        label (MessageAssessmentLabel | None): The assessment label (e.g. "NEGATIVE")

    Returns:
        MessageAssessment: The modified message assessment

    Raises:
        Exception: If the modification fails

    """
    try:
        assessment = await unique_sdk.MessageAssessment.modify_async(
            user_id=user_id,
            company_id=company_id,
            messageId=assistant_message_id,
            status=status.name if status else None,
            title=title,
            explanation=explanation,
            label=label.name if label else None,
            type=type.name,
        )
        return ChatMessageAssessment(**assessment)
    except Exception as e:
        logger.error(f"Failed to modify message assessment: {e}")
        raise e


@deprecated("Use stream_complete_with_references instead")
def stream_complete_to_chat(
    company_id: str,
    user_id: str,
    assistant_message_id: str,
    user_message_id: str,
    chat_id: str,
    assistant_id: str,
    messages: LanguageModelMessages | list[ChatCompletionMessageParam],
    model_name: LanguageModelName | str,
    content_chunks: list[ContentChunk] | None = None,
    debug_info: dict = {},
    temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
    timeout: int = DEFAULT_COMPLETE_TIMEOUT,
    tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
    start_text: str | None = None,
    other_options: dict | None = None,
) -> LanguageModelStreamResponse:
    return stream_complete_with_references(
        company_id=company_id,
        user_id=user_id,
        assistant_message_id=assistant_message_id,
        user_message_id=user_message_id,
        chat_id=chat_id,
        assistant_id=assistant_id,
        messages=messages,
        model_name=model_name,
        content_chunks=content_chunks,
        debug_info=debug_info,
        temperature=temperature,
        timeout=timeout,
        tools=tools,
        start_text=start_text,
        other_options=other_options,
    )


def stream_complete_with_references(
    company_id: str,
    user_id: str,
    assistant_message_id: str,
    user_message_id: str,
    chat_id: str,
    assistant_id: str,
    messages: LanguageModelMessages | list[ChatCompletionMessageParam],
    model_name: LanguageModelName | str,
    content_chunks: list[ContentChunk] | None = None,
    debug_info: dict | None = None,
    temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
    timeout: int = DEFAULT_COMPLETE_TIMEOUT,
    tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
    start_text: str | None = None,
    other_options: dict | None = None,
) -> LanguageModelStreamResponse:
    """Streams a completion synchronously.

    Args:
        company_id (str): The company ID associated with the request.
        user_id (str): The user ID for the request.
        assistant_message_id (str): The assistant message ID.
        user_message_id (str): The user message ID.
        chat_id (str): The chat ID.
        assistant_id (str): The assistant ID.
        messages (LanguageModelMessages): The messages to complete.
        model_name (LanguageModelName | str): The model name.
        content_chunks (list[ContentChunk]): Content chunks for context.
        debug_info (dict): Debug information.
        temperature (float): Temperature setting.
        timeout (int): Timeout in milliseconds.
        tools (Optional[list[LanguageModelTool | LanguageModelToolDescription ]]): Optional tools.
        start_text (Optional[str]): Starting text.
        other_options (Optional[dict]): Additional options.

    Returns:
        LanguageModelStreamResponse: The streaming response object.

    """
    options, model, messages_dict, search_context = (
        _prepare_all_completions_params_util(
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            tools=tools,
            other_options=other_options,
            content_chunks=content_chunks or [],
        )
    )

    try:
        response = unique_sdk.Integrated.chat_stream_completion(
            user_id=user_id,
            company_id=company_id,
            assistantMessageId=assistant_message_id,
            userMessageId=user_message_id,
            messages=messages_dict,
            chatId=chat_id,
            searchContext=search_context,
            model=model,
            timeout=timeout,
            assistantId=assistant_id,
            debugInfo=debug_info or {},
            options=options,  # type: ignore
            startText=start_text,
        )
        return LanguageModelStreamResponse(**response)
    except Exception as e:
        logger.error(f"Error streaming completion: {e}")
        raise e


@deprecated("Use stream_complete_with_references_async instead")
async def stream_complete_to_chat_async(
    company_id: str,
    user_id: str,
    assistant_message_id: str,
    user_message_id: str,
    chat_id: str,
    assistant_id: str,
    messages: LanguageModelMessages | list[ChatCompletionMessageParam],
    model_name: LanguageModelName | str,
    content_chunks: list[ContentChunk] | None = None,
    debug_info: dict = {},
    temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
    timeout: int = DEFAULT_COMPLETE_TIMEOUT,
    tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
    start_text: str | None = None,
    other_options: dict | None = None,
) -> LanguageModelStreamResponse:
    return await stream_complete_with_references_async(
        company_id=company_id,
        user_id=user_id,
        assistant_message_id=assistant_message_id,
        user_message_id=user_message_id,
        chat_id=chat_id,
        assistant_id=assistant_id,
        messages=messages,
        model_name=model_name,
        content_chunks=content_chunks,
        debug_info=debug_info,
        temperature=temperature,
        timeout=timeout,
        tools=tools,
        start_text=start_text,
        other_options=other_options,
    )


async def stream_complete_with_references_async(
    company_id: str,
    user_id: str,
    assistant_message_id: str,
    user_message_id: str,
    chat_id: str,
    assistant_id: str,
    messages: LanguageModelMessages | list[ChatCompletionMessageParam],
    model_name: LanguageModelName | str,
    content_chunks: list[ContentChunk] | None = None,
    debug_info: dict | None = None,
    temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
    timeout: int = DEFAULT_COMPLETE_TIMEOUT,
    tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
    start_text: str | None = None,
    other_options: dict | None = None,
) -> LanguageModelStreamResponse:
    """Streams a completion asynchronously.

    Args: [same as stream_complete]

    Returns:
        LanguageModelStreamResponse: The streaming response object.

    """
    options, model, messages_dict, search_context = (
        _prepare_all_completions_params_util(
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            tools=tools,
            other_options=other_options,
            content_chunks=content_chunks or [],
        )
    )

    try:
        response = await unique_sdk.Integrated.chat_stream_completion_async(
            user_id=user_id,
            company_id=company_id,
            assistantMessageId=assistant_message_id,
            userMessageId=user_message_id,
            messages=messages_dict,
            chatId=chat_id,
            searchContext=search_context,
            model=model,
            timeout=timeout,
            assistantId=assistant_id,
            debugInfo=debug_info or {},
            options=options,  # type: ignore
            startText=start_text,
        )
        return LanguageModelStreamResponse(**response)
    except Exception as e:
        logger.error(f"Error streaming completion: {e}")
        raise e


def create_message_log(
    user_id: str,
    company_id: str,
    message_id: str,
    text: str,
    status: MessageLogStatus,
    order: int,
    details: MessageLogDetails | None = None,
    uncited_references: MessageLogUncitedReferences | None = None,
    references: list[ContentReference] | None = None,
) -> MessageLog:
    """Creates a message log synchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        message_id (str): The ID of the message this log belongs to.
        text (str): The log text content.
        status (MessageLogStatus): The status of this log entry.
        order (int): The order/sequence number of this log entry.
        details (MessageLogDetails | None): Additional details about this log entry.
        uncited_references (MessageLogUncitedReferences | None): References that are not cited.
        references (list[ContentReference] | None): List of references for this log.

    Returns:
        MessageLog: The created message log.

    Raises:
        Exception: If the creation fails.

    """
    try:
        message_log = unique_sdk.MessageLog.create(
            user_id=user_id,
            company_id=company_id,
            messageId=message_id,
            text=text,
            status=status.value,
            order=order,
            details=details.model_dump() if details else None,
            uncitedReferences=uncited_references.model_dump()
            if uncited_references
            else None,
            references=map_references_with_original_index(references)
            if references
            else [],  # type: ignore
        )
        return MessageLog(**message_log)
    except Exception as e:
        logger.error(f"Failed to create message log: {e}")
        raise e


async def create_message_log_async(
    user_id: str,
    company_id: str,
    message_id: str,
    text: str,
    status: MessageLogStatus,
    order: int,
    details: MessageLogDetails | None = None,
    uncited_references: MessageLogUncitedReferences | None = None,
    references: list[ContentReference] | None = None,
) -> MessageLog:
    """Creates a message log asynchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        message_id (str): The ID of the message this log belongs to.
        text (str): The log text content.
        status (MessageLogStatus): The status of this log entry.
        order (int): The order/sequence number of this log entry.
        details (MessageLogDetails | None): Additional details about this log entry.
        uncited_references (MessageLogUncitedReferences | None): References that are not cited.
        references (list[ContentReference] | None): List of references for this log.

    Returns:
        MessageLog: The created message log.

    Raises:
        Exception: If the creation fails.

    """
    try:
        message_log = await unique_sdk.MessageLog.create_async(
            user_id=user_id,
            company_id=company_id,
            messageId=message_id,
            text=text,
            status=status.value,
            order=order,
            details=details.model_dump() if details else None,
            uncitedReferences=uncited_references.model_dump()
            if uncited_references
            else None,
            references=map_references_with_original_index(references)
            if references
            else [],  # type: ignore
        )
        return MessageLog(**message_log)
    except Exception as e:
        logger.error(f"Failed to create message log: {e}")
        raise e


def update_message_log(
    user_id: str,
    company_id: str,
    message_log_id: str,
    order: int,
    text: str | None = None,
    status: MessageLogStatus | None = None,
    details: MessageLogDetails | None = None,
    uncited_references: MessageLogUncitedReferences | None = None,
    references: list[ContentReference] | None = None,
) -> MessageLog:
    """Updates a message log synchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        message_log_id (str): The ID of the message log to update.
        order (int): The order/sequence number (required).
        text (str | None): The updated log text content.
        status (MessageLogStatus | None): The updated status.
        details (MessageLogDetails | None): Updated additional details.
        uncited_references (MessageLogUncitedReferences | None): Updated uncited references.
        references (list[ContentReference] | None): Updated list of references.

    Returns:
        MessageLog: The updated message log.

    Raises:
        Exception: If the update fails.

    """
    try:
        message_log = unique_sdk.MessageLog.update(
            user_id=user_id,
            company_id=company_id,
            message_log_id=message_log_id,
            text=text,
            status=status.value if status else None,
            order=order,
            details=details.model_dump() if details else None,
            uncitedReferences=uncited_references.model_dump()
            if uncited_references
            else None,
            references=map_references_with_original_index(references)
            if references
            else [],  # type: ignore
        )
        return MessageLog(**message_log)
    except Exception as e:
        logger.error(f"Failed to update message log: {e}")
        raise e


async def update_message_log_async(
    user_id: str,
    company_id: str,
    message_log_id: str,
    order: int,
    text: str | None = None,
    status: MessageLogStatus | None = None,
    details: MessageLogDetails | None = None,
    uncited_references: MessageLogUncitedReferences | None = None,
    references: list[ContentReference] | None = None,
) -> MessageLog:
    """Updates a message log asynchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        message_log_id (str): The ID of the message log to update.
        order (int): The order/sequence number (required).
        text (str | None): The updated log text content.
        status (MessageLogStatus | None): The updated status.
        details (MessageLogDetails | None): Updated additional details.
        uncited_references (MessageLogUncitedReferences | None): Updated uncited references.
        references (list[ContentReference] | None): Updated list of references.

    Returns:
        MessageLog: The updated message log.

    Raises:
        Exception: If the update fails.

    """
    try:
        message_log = await unique_sdk.MessageLog.update_async(
            user_id=user_id,
            company_id=company_id,
            message_log_id=message_log_id,
            text=text,
            status=status.value if status else None,
            order=order,
            details=details.model_dump() if details else None,
            uncitedReferences=uncited_references.model_dump()
            if uncited_references
            else None,
            references=map_references_with_original_index(references)
            if references
            else [],  # type: ignore
        )
        return MessageLog(**message_log)
    except Exception as e:
        logger.error(f"Failed to update message log: {e}")
        raise e


def create_message_execution(
    user_id: str,
    company_id: str,
    message_id: str,
    chat_id: str,
    type: MessageExecutionType = MessageExecutionType.DEEP_RESEARCH,
    seconds_remaining: int | None = None,
    percentage_completed: int | None = None,
) -> MessageExecution:
    """Creates a message execution synchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        message_id (str): The ID of the message this execution belongs to.
        chat_id (str): The chat ID.
        type (MessageExecutionType): The type of execution. Defaults to DEEP_RESEARCH.
        seconds_remaining (int | None): Estimated seconds remaining for completion.
        percentage_completed (int | None): Percentage of completion (0-100).

    Returns:
        MessageExecution: The created message execution.

    Raises:
        Exception: If the creation fails.

    """
    try:
        message_execution = unique_sdk.MessageExecution.create(
            user_id=user_id,
            company_id=company_id,
            messageId=message_id,
            chatId=chat_id,
            type=type.value,
            secondsRemaining=seconds_remaining,
            percentageCompleted=percentage_completed,
        )
        return MessageExecution(**message_execution)
    except Exception as e:
        logger.error(f"Failed to create message execution: {e}")
        raise e


async def create_message_execution_async(
    user_id: str,
    company_id: str,
    message_id: str,
    chat_id: str,
    type: MessageExecutionType = MessageExecutionType.DEEP_RESEARCH,
    seconds_remaining: int | None = None,
    percentage_completed: int | None = None,
) -> MessageExecution:
    """Creates a message execution asynchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        message_id (str): The ID of the message this execution belongs to.
        chat_id (str): The chat ID.
        type (MessageExecutionType): The type of execution. Defaults to DEEP_RESEARCH.
        seconds_remaining (int | None): Estimated seconds remaining for completion.
        percentage_completed (int | None): Percentage of completion (0-100).

    Returns:
        MessageExecution: The created message execution.

    Raises:
        Exception: If the creation fails.

    """
    try:
        message_execution = await unique_sdk.MessageExecution.create_async(
            user_id=user_id,
            company_id=company_id,
            messageId=message_id,
            chatId=chat_id,
            type=type.value,
            secondsRemaining=seconds_remaining,
            percentageCompleted=percentage_completed,
        )
        return MessageExecution(**message_execution)
    except Exception as e:
        logger.error(f"Failed to create message execution: {e}")
        raise e


def get_message_execution(
    user_id: str,
    company_id: str,
    message_id: str,
) -> MessageExecution:
    """Gets a message execution by message ID synchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        message_id (str): The ID of the message to get execution for.

    Returns:
        MessageExecution: The message execution.

    Raises:
        Exception: If the retrieval fails.

    """
    try:
        message_execution = unique_sdk.MessageExecution.get(
            user_id=user_id,
            company_id=company_id,
            messageId=message_id,
        )
        return MessageExecution(**message_execution)
    except Exception as e:
        logger.error(f"Failed to get message execution: {e}")
        raise e


async def get_message_execution_async(
    user_id: str,
    company_id: str,
    message_id: str,
) -> MessageExecution:
    """Gets a message execution by message ID asynchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        message_id (str): The ID of the message to get execution for.

    Returns:
        MessageExecution: The message execution.

    Raises:
        Exception: If the retrieval fails.

    """
    try:
        message_execution = await unique_sdk.MessageExecution.get_async(
            user_id=user_id,
            company_id=company_id,
            messageId=message_id,
        )
        return MessageExecution(**message_execution)
    except Exception as e:
        logger.error(f"Failed to get message execution: {e}")
        raise e


def update_message_execution(
    user_id: str,
    company_id: str,
    message_id: str,
    status: MessageExecutionUpdateStatus,
    seconds_remaining: int | None = None,
    percentage_completed: int | None = None,
) -> MessageExecution:
    """Updates a message execution synchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        message_id (str): The ID of the message to update execution for.
        status (MessageExecutionUpdateStatus): The updated status (COMPLETED or FAILED).
        seconds_remaining (int | None): Updated estimated seconds remaining.
        percentage_completed (int | None): Updated percentage of completion (0-100).

    Returns:
        MessageExecution: The updated message execution.

    Raises:
        Exception: If the update fails.

    """
    try:
        message_execution = unique_sdk.MessageExecution.update(
            user_id=user_id,
            company_id=company_id,
            messageId=message_id,
            status=status.value,
            secondsRemaining=seconds_remaining,
            percentageCompleted=percentage_completed,
        )
        return MessageExecution(**message_execution)
    except Exception as e:
        logger.error(f"Failed to update message execution: {e}")
        raise e


async def update_message_execution_async(
    user_id: str,
    company_id: str,
    message_id: str,
    status: MessageExecutionUpdateStatus,
    seconds_remaining: int | None = None,
    percentage_completed: int | None = None,
) -> MessageExecution:
    """Updates a message execution asynchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        message_id (str): The ID of the message to update execution for.
        status (MessageExecutionUpdateStatus): The updated status (COMPLETED or FAILED).
        seconds_remaining (int | None): Updated estimated seconds remaining.
        percentage_completed (int | None): Updated percentage of completion (0-100).

    Returns:
        MessageExecution: The updated message execution.

    Raises:
        Exception: If the update fails.

    """
    try:
        message_execution = await unique_sdk.MessageExecution.update_async(
            user_id=user_id,
            company_id=company_id,
            messageId=message_id,
            status=status.value,
            secondsRemaining=seconds_remaining,
            percentageCompleted=percentage_completed,
        )
        return MessageExecution(**message_execution)
    except Exception as e:
        logger.error(f"Failed to update message execution: {e}")
        raise e


def _convert_tools_to_openai(
    tools: Sequence[LanguageModelToolDescription | ToolParam],
) -> list[ToolParam]:
    openai_tools = []
    for tool in tools:
        if isinstance(tool, LanguageModelToolDescription):
            openai_tools.append(tool.to_openai(mode="responses"))
        else:
            openai_tools.append(tool)
    return openai_tools


def _convert_messages_to_openai(
    messages: Sequence[ResponseInputItemParam | LanguageModelMessageOptions],
) -> list[ResponseInputParam]:
    res = []
    for message in messages:
        if isinstance(message, LanguageModelMessageOptions):
            if isinstance(message, LanguageModelMessage):
                message = message.to_specific_message()

            if isinstance(message, LanguageModelAssistantMessage):
                res.extend(message.to_openai(mode="responses"))
            else:
                res.append(message.to_openai(mode="responses"))
        else:
            res.append(message)

    return res


class _ResponsesParams(NamedTuple):
    temperature: float
    model_name: str
    search_context: SearchContext | None
    messages: str | list[ResponseInputParam]
    tools: list[ToolParam] | None


def _prepare_responses_params_util(
    model_name: LanguageModelName | str,
    content_chunks: list[ContentChunk] | None,
    temperature: float,
    tools: Sequence[LanguageModelToolDescription | ToolParam] | None,
    messages: str
    | LanguageModelMessages
    | Sequence[ResponseInputItemParam | LanguageModelMessageOptions],
) -> _ResponsesParams:
    search_context = (
        _to_search_context(content_chunks) if content_chunks is not None else None
    )

    model = model_name.name if isinstance(model_name, LanguageModelName) else model_name

    if isinstance(model_name, LanguageModelName):
        model_info = LanguageModelInfo.from_name(model_name)

        if model_info.temperature_bounds is not None and temperature is not None:
            temperature = _clamp_temperature(temperature, model_info.temperature_bounds)

    messages_res = None
    if isinstance(messages, LanguageModelMessages):
        messages_res = _convert_messages_to_openai(messages.root)
    elif isinstance(messages, list):
        messages_res = _convert_messages_to_openai(messages)
    else:
        assert isinstance(messages, str)
        messages_res = messages

    tools_res = _convert_tools_to_openai(tools) if tools is not None else None
    return _ResponsesParams(temperature, model, search_context, messages_res, tools_res)


def _prepare_responses_args(
    company_id: str,
    user_id: str,
    assistant_message_id: str,
    user_message_id: str,
    chat_id: str,
    assistant_id: str,
    params: _ResponsesParams,
    temperature: float,
    debug_info: dict | None,
    start_text: str | None,
    include: list[ResponseIncludable] | None,
    instructions: str | None,
    max_output_tokens: int | None,
    metadata: Metadata | None,
    parallel_tool_calls: bool | None,
    text: ResponseTextConfigParam | None,
    tool_choice: response_create_params.ToolChoice | None,
    top_p: float | None,
    reasoning: Reasoning | None,
    other_options: dict | None = None,
) -> dict[str, Any]:
    options = {}

    options["company_id"] = company_id
    options["user_id"] = user_id

    options["model"] = params.model_name

    if params.search_context is not None:
        options["searchContext"] = params.search_context

    options["chatId"] = chat_id
    options["assistantId"] = assistant_id
    options["assistantMessageId"] = assistant_message_id
    options["userMessageId"] = user_message_id

    if debug_info is not None:
        options["debugInfo"] = debug_info
    if start_text is not None:
        options["startText"] = start_text

    options["input"] = params.messages

    openai_options: unique_sdk.Integrated.CreateStreamResponsesOpenaiParams = {}

    if include is not None:
        openai_options["include"] = include

    if instructions is not None:
        openai_options["instructions"] = instructions

    if max_output_tokens is not None:
        openai_options["max_output_tokens"] = max_output_tokens

    if metadata is not None:
        openai_options["metadata"] = metadata

    if parallel_tool_calls is not None:
        openai_options["parallel_tool_calls"] = parallel_tool_calls

    if temperature is not None:
        openai_options["temperature"] = temperature

    if text is not None:
        openai_options["text"] = text

    if tool_choice is not None:
        openai_options["tool_choice"] = tool_choice

    if params.tools is not None:
        openai_options["tools"] = params.tools

    if top_p is not None:
        openai_options["top_p"] = top_p

    if reasoning is not None:
        openai_options["reasoning"] = reasoning

    # allow any other openai.resources.responses.Response.create options
    if other_options is not None:
        openai_options.update(other_options)  # type: ignore

    options["options"] = openai_options

    return options


def stream_responses_with_references(
    *,
    company_id: str,
    user_id: str,
    assistant_message_id: str,
    user_message_id: str,
    chat_id: str,
    assistant_id: str,
    model_name: LanguageModelName | str,
    messages: str
    | LanguageModelMessages
    | Sequence[ResponseInputItemParam | LanguageModelMessageOptions],
    content_chunks: list[ContentChunk] | None = None,
    tools: Sequence[LanguageModelToolDescription | ToolParam] | None = None,
    temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
    debug_info: dict | None = None,
    start_text: str | None = None,
    include: list[ResponseIncludable] | None = None,
    instructions: str | None = None,
    max_output_tokens: int | None = None,
    metadata: Metadata | None = None,
    parallel_tool_calls: bool | None = None,
    text: ResponseTextConfigParam | None = None,
    tool_choice: response_create_params.ToolChoice | None = None,
    top_p: float | None = None,
    reasoning: Reasoning | None = None,
    other_options: dict | None = None,
) -> ResponsesLanguageModelStreamResponse:
    responses_params = _prepare_responses_params_util(
        model_name=model_name,
        content_chunks=content_chunks,
        temperature=temperature,
        tools=tools,
        messages=messages,
    )

    responses_args = _prepare_responses_args(
        company_id=company_id,
        user_id=user_id,
        assistant_message_id=assistant_message_id,
        user_message_id=user_message_id,
        chat_id=chat_id,
        assistant_id=assistant_id,
        params=responses_params,
        temperature=temperature,
        debug_info=debug_info,
        start_text=start_text,
        include=include,
        instructions=instructions,
        max_output_tokens=max_output_tokens,
        metadata=metadata,
        parallel_tool_calls=parallel_tool_calls,
        text=text,
        tool_choice=tool_choice,
        top_p=top_p,
        reasoning=reasoning,
        other_options=other_options,
    )

    return ResponsesLanguageModelStreamResponse.model_validate(
        unique_sdk.Integrated.responses_stream(
            **responses_args,
        )
    )


async def stream_responses_with_references_async(
    *,
    company_id: str,
    user_id: str,
    assistant_message_id: str,
    user_message_id: str,
    chat_id: str,
    assistant_id: str,
    model_name: LanguageModelName | str,
    messages: str
    | LanguageModelMessages
    | Sequence[ResponseInputItemParam | LanguageModelMessageOptions],
    content_chunks: list[ContentChunk] | None = None,
    tools: Sequence[LanguageModelToolDescription | ToolParam] | None = None,
    temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
    debug_info: dict | None = None,
    start_text: str | None = None,
    include: list[ResponseIncludable] | None = None,
    instructions: str | None = None,
    max_output_tokens: int | None = None,
    metadata: Metadata | None = None,
    parallel_tool_calls: bool | None = None,
    text: ResponseTextConfigParam | None = None,
    tool_choice: response_create_params.ToolChoice | None = None,
    top_p: float | None = None,
    reasoning: Reasoning | None = None,
    other_options: dict | None = None,
) -> ResponsesLanguageModelStreamResponse:
    responses_params = _prepare_responses_params_util(
        model_name=model_name,
        content_chunks=content_chunks,
        temperature=temperature,
        tools=tools,
        messages=messages,
    )

    responses_args = _prepare_responses_args(
        company_id=company_id,
        user_id=user_id,
        assistant_message_id=assistant_message_id,
        user_message_id=user_message_id,
        chat_id=chat_id,
        assistant_id=assistant_id,
        params=responses_params,
        temperature=temperature,
        debug_info=debug_info,
        start_text=start_text,
        include=include,
        instructions=instructions,
        max_output_tokens=max_output_tokens,
        metadata=metadata,
        parallel_tool_calls=parallel_tool_calls,
        text=text,
        tool_choice=tool_choice,
        top_p=top_p,
        reasoning=reasoning,
        other_options=other_options,
    )

    return ResponsesLanguageModelStreamResponse.model_validate(
        await unique_sdk.Integrated.responses_stream_async(
            **responses_args,
        )
    )
