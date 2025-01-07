import logging
import re
from typing import Any, Dict, List, Optional

import unique_sdk
from unique_sdk._list_object import ListObject

from unique_toolkit._common import _time_utils
from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.content.utils import count_tokens

logger = logging.getLogger(__name__)


def map_references(references: List[ContentReference]) -> List[Dict[str, Any]]:
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


def construct_message_modify_params(
    event_user_id: str,
    event_company_id: str,
    event_payload_chat_id: str,
    event_payload_assistant_message_id: str,
    event_payload_user_message_id: str,
    event_payload_user_message_text: str,
    assistant: bool = True,
    content: Optional[str] = None,
    original_content: Optional[str] = None,
    references: Optional[list[ContentReference]] = None,
    debug_info: Optional[dict] = None,
    message_id: Optional[str] = None,
    set_completed_at: Optional[bool] = False,
) -> Dict[str, Any]:
    completed_at_datetime = None

    if message_id:
        # Message ID specified. No need to guess
        message_id = message_id
    elif assistant:
        # Assistant message ID
        message_id = event_payload_assistant_message_id
    else:
        message_id = event_payload_user_message_id
        if content is None:
            content = event_payload_user_message_text

    if set_completed_at:
        completed_at_datetime = _time_utils.get_datetime_now()

    params = {
        "user_id": event_user_id,
        "company_id": event_company_id,
        "id": message_id,
        "chatId": event_payload_chat_id,
        "text": content,
        "originalText": original_content,
        "references": map_references(references) if references else [],
        "debugInfo": debug_info,
        "completedAt": completed_at_datetime,
    }
    return params


def construct_message_create_params(
    event_user_id: str,
    event_company_id: str,
    event_payload_chat_id: str,
    event_payload_assistant_id: str,
    role: ChatMessageRole = ChatMessageRole.ASSISTANT,
    content: Optional[str] = None,
    original_content: Optional[str] = None,
    references: Optional[list[ContentReference]] = None,
    debug_info: Optional[dict] = None,
    assistantId: Optional[str] = None,
    set_completed_at: Optional[bool] = False,
) -> Dict[str, Any]:
    if assistantId is None:
        # if Assistant ID isn't specified. change event_payload_assistant.
        assistantId = event_payload_assistant_id

    if original_content is None:
        original_content = content

    params = {
        "user_id": event_user_id,
        "company_id": event_company_id,
        "assistantId": assistantId,
        "role": role.value.upper(),
        "chatId": event_payload_chat_id,
        "text": content,
        "originalText": original_content,
        "references": map_references(references) if references else [],
        "debugInfo": debug_info,
        "completedAt": _time_utils.get_datetime_now() if set_completed_at else None,
    }
    return params


def get_selection_from_history(
    full_history: list[ChatMessage],
    max_tokens: int,
    max_messages=4,
) -> List[ChatMessage]:
    messages = full_history[-max_messages:]
    filtered_messages = [m for m in messages if m.content]
    mapped_messages = []

    for m in filtered_messages:
        m.content = re.sub(r"<sup>\d+</sup>", "", m.content)
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


def map_to_chat_messages(messages: list[dict]) -> List[ChatMessage]:
    return [ChatMessage(**msg) for msg in messages]


def pick_messages_in_reverse_for_token_window(
    messages: list[ChatMessage],
    limit: int,
) -> List[ChatMessage]:
    if len(messages) < 1 or limit < 1:
        return []

    last_index = len(messages) - 1
    token_count = count_tokens(messages[last_index].content)
    while token_count > limit:
        logger.debug(
            f"Limit too low for the initial message. Last message TokenCount {token_count} available tokens {limit} - cutting message in half until it fits"
        )
        content = messages[last_index].content
        messages[last_index].content = content[: len(content) // 2] + "..."
        token_count = count_tokens(messages[last_index].content)

    while token_count <= limit and last_index > 0:
        token_count = count_tokens(
            "".join([msg.content for msg in messages[:last_index]])
        )
        if token_count <= limit:
            last_index -= 1

    last_index = max(0, last_index)
    return messages[last_index:]


def trigger_list_messages(
    event_user_id, event_company_id, chat_id: str
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


async def trigger_list_messages_async(
    event_user_id: str, event_company_id: str, chat_id: str
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
    event_user_id, event_company_id, event_payload_chat_id
) -> List[ChatMessage]:
    messages = trigger_list_messages(
        event_user_id, event_company_id, event_payload_chat_id
    )
    messages = filter_valid_messages(messages)

    return map_to_chat_messages(messages)


async def get_full_history_async(
    event_user_id, event_company_id, event_payload_chat_id
) -> List[ChatMessage]:
    messages = await trigger_list_messages_async(
        event_user_id, event_company_id, event_payload_chat_id
    )
    messages = filter_valid_messages(messages)

    return map_to_chat_messages(messages)


def filter_valid_messages(
    messages: ListObject[unique_sdk.Message],
) -> List[Dict[str, Any]]:
    SYSTEM_MESSAGE_PREFIX = "[SYSTEM] "

    # Remove the last two messages
    messages = messages["data"][:-2]  # type: ignore
    filtered_messages = []
    for message in messages:
        if message["text"] is None:
            continue
        elif SYSTEM_MESSAGE_PREFIX in message["text"]:
            continue
        else:
            filtered_messages.append(message)

    return filtered_messages
