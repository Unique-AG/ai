import logging
from typing import Optional

import unique_sdk

from unique_toolkit._common import _time_utils
from unique_toolkit.chat.constants import DOMAIN_NAME
from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.chat.utils import (
    filter_valid_messages,
    map_references,
    map_to_chat_messages,
)
from unique_toolkit.content.schemas import ContentReference

logger = logging.getLogger(f"toolkit.{DOMAIN_NAME}.{__name__}")


async def update_message_debug_info_async(
    user_id: str,
    company_id: str,
    message_id: str,
    chat_id: str,
    debug_info: dict,
) -> None:
    """Updates the debug information for a message asynchronously."""
    try:
        await unique_sdk.Message.modify_async(
            user_id=user_id,
            company_id=company_id,
            id=message_id,
            chatId=chat_id,
            debugInfo=debug_info,
            references=[],
            completedAt=None,
        )
    except Exception as e:
        logger.error(f"Failed to update debug info: {e}")
        raise e


def update_message_debug_info(
    user_id: str,
    company_id: str,
    message_id: str,
    chat_id: str,
    debug_info: dict,
) -> None:
    """Updates the debug information for a message synchronously."""
    try:
        unique_sdk.Message.modify(
            user_id=user_id,
            company_id=company_id,
            id=message_id,
            chatId=chat_id,
            debugInfo=debug_info,
            references=[],
            completedAt=None,
        )
    except Exception as e:
        logger.error(f"Failed to update debug info: {e}")
        raise e


def modify_message(
    user_id: str,
    company_id: str,
    message_id: str,
    chat_id: str,
    content: Optional[str] = None,
    original_content: Optional[str] = None,
    references: Optional[list[ContentReference]] = None,
    debug_info: Optional[dict] = None,
    set_completed_at: bool = False,
) -> ChatMessage:
    """Modifies a message synchronously."""
    try:
        completed_at = _time_utils.get_datetime_now() if set_completed_at else None
        message = unique_sdk.Message.modify(
            user_id=user_id,
            company_id=company_id,
            id=message_id,
            chatId=chat_id,
            text=content,
            originalText=original_content,  # type: ignore
            references=map_references(references) if references else [],
            debugInfo=debug_info,
            completedAt=completed_at,
        )
        return ChatMessage(**message)
    except Exception as e:
        logger.error(f"Failed to modify message: {e}")
        raise e


async def modify_message_async(
    user_id: str,
    company_id: str,
    message_id: str,
    chat_id: str,
    content: Optional[str] = None,
    original_content: Optional[str] = None,
    references: Optional[list[ContentReference]] = None,
    debug_info: Optional[dict] = None,
    set_completed_at: bool = False,
) -> ChatMessage:
    """Modifies a message asynchronously."""
    try:
        completed_at = _time_utils.get_datetime_now() if set_completed_at else None
        message = await unique_sdk.Message.modify_async(
            user_id=user_id,
            company_id=company_id,
            id=message_id,
            chatId=chat_id,
            text=content,
            originalText=original_content,  # type: ignore
            references=map_references(references) if references else [],
            debugInfo=debug_info,
            completedAt=completed_at,
        )
        return ChatMessage(**message)
    except Exception as e:
        logger.error(f"Failed to modify message: {e}")
        raise e


def create_message(
    user_id: str,
    company_id: str,
    chat_id: str,
    assistant_id: str,
    role: ChatMessageRole,
    content: str,
    original_content: Optional[str] = None,
    references: Optional[list[ContentReference]] = None,
    debug_info: Optional[dict] = None,
    set_completed_at: bool = False,
) -> ChatMessage:
    """Creates a new message synchronously."""
    try:
        completed_at = _time_utils.get_datetime_now() if set_completed_at else None
        message = unique_sdk.Message.create(
            user_id=user_id,
            company_id=company_id,
            assistantId=assistant_id,
            chatId=chat_id,
            role=role.value,
            text=content,
            originalText=original_content or content,  # type: ignore
            references=map_references(references) if references else [],
            debugInfo=debug_info,
            completedAt=completed_at,
        )
        return ChatMessage(**message)
    except Exception as e:
        logger.error(f"Failed to create message: {e}")
        raise e


async def create_message_async(
    user_id: str,
    company_id: str,
    chat_id: str,
    assistant_id: str,
    content: str,
    role: ChatMessageRole,
    original_content: Optional[str] = None,
    references: Optional[list[ContentReference]] = None,
    debug_info: Optional[dict] = None,
    set_completed_at: bool = False,
) -> ChatMessage:
    """Creates a new message asynchronously."""
    try:
        completed_at = _time_utils.get_datetime_now() if set_completed_at else None
        message = await unique_sdk.Message.create_async(
            user_id=user_id,
            company_id=company_id,
            assistantId=assistant_id,
            chatId=chat_id,
            role=role.value,
            text=content,
            originalText=original_content or content,  # type: ignore
            references=map_references(references) if references else [],
            debugInfo=debug_info,
            completedAt=completed_at,
        )
        return ChatMessage(**message)
    except Exception as e:
        logger.error(f"Failed to create message: {e}")
        raise e


def list_messages(
    user_id: str,
    company_id: str,
    chat_id: str,
) -> list[ChatMessage]:
    """Lists messages for a chat synchronously."""
    try:
        messages = unique_sdk.Message.list(
            user_id=user_id,
            company_id=company_id,
            chatId=chat_id,
        )
        filtered = filter_valid_messages(messages)
        return map_to_chat_messages(filtered)
    except Exception as e:
        logger.error(f"Failed to list messages: {e}")
        raise e


async def list_messages_async(
    user_id: str,
    company_id: str,
    chat_id: str,
) -> list[ChatMessage]:
    """Lists messages for a chat asynchronously."""
    try:
        messages = await unique_sdk.Message.list_async(
            user_id=user_id,
            company_id=company_id,
            chatId=chat_id,
        )
        filtered = filter_valid_messages(messages)
        return map_to_chat_messages(filtered)
    except Exception as e:
        logger.error(f"Failed to list messages: {e}")
        raise e
