import json
import logging

import unique_sdk
from typing_extensions import Any

from unique_toolkit.short_term_memory.constants import DOMAIN_NAME
from unique_toolkit.short_term_memory.schemas import ShortTermMemory

logger = logging.getLogger(f"toolkit.{DOMAIN_NAME}.{__name__}")


async def find_latest_memory_async(
    user_id: str,
    company_id: str,
    key: str,
    chat_id: str | None = None,
    message_id: str | None = None,
) -> ShortTermMemory:
    """
    Find the latest short term memory asynchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        key (str): The key.
        chat_id (str | None): The chat ID.
        message_id (str | None): The message ID.

    Returns:
        ShortTermMemory: The latest short term memory.

    Raises:
        Exception: If an error occurs.
    """
    try:
        logger.info("Finding latest short term memory")
        stm = await unique_sdk.ShortTermMemory.find_latest_async(
            user_id=user_id,
            company_id=company_id,
            memoryName=key,
            chatId=chat_id,
            messageId=message_id,
        )
        return ShortTermMemory.model_validate(stm, by_alias=True, by_name=True)
    except Exception as e:
        logger.error(f"Error finding latest short term memory: {e}")
        raise e


def find_latest_memory(
    user_id: str,
    company_id: str,
    key: str,
    chat_id: str | None = None,
    message_id: str | None = None,
) -> ShortTermMemory:
    """
    Find the latest short term memory.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        key (str): The key.
        chat_id (str | None): The chat ID.
        message_id (str | None): The message ID.

    Returns:
        ShortTermMemory: The latest short term memory.

    Raises:
        Exception: If an error occurs.
    """
    try:
        logger.info("Finding latest short term memory")
        stm = unique_sdk.ShortTermMemory.find_latest(
            user_id=user_id,
            company_id=company_id,
            memoryName=key,
            chatId=chat_id,
            messageId=message_id,
        )
        return ShortTermMemory.model_validate(stm, by_alias=True, by_name=True)
    except Exception as e:
        logger.error(f"Error finding latest short term memory: {e}")
        raise e


async def create_memory_async(
    user_id: str,
    company_id: str,
    key: str,
    value: str | dict,
    chat_id: str | None = None,
    message_id: str | None = None,
):
    """
    Create a short term memory asynchronously.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        key (str): The key.
        value (str | dict): The value.
        chat_id (str | None): The chat ID.
        message_id (str | None): The message ID.

    Returns:
        ShortTermMemory: The created short term memory.

    Raises:
        Exception: If an error occurs.
    """

    if isinstance(value, dict):
        value = json.dumps(value)

    try:
        logger.info("Creating short term memory")
        stm = await unique_sdk.ShortTermMemory.create_async(
            user_id=user_id,
            company_id=company_id,
            memoryName=key,
            chatId=chat_id,
            messageId=message_id,
            data=value,
        )
        return ShortTermMemory.model_validate(stm, by_alias=True, by_name=True)
    except Exception as e:
        logger.error(f"Error creating short term memory: {e}")
        raise e


def create_memory(
    *,
    user_id: str,
    company_id: str,
    key: str,
    value: str | dict,
    chat_id: str | None = None,
    message_id: str | None = None,
):
    """
    Create a short term memory.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        key (str): The key.
        value (str | dict): The value.
        chat_id (str | None): The chat ID.
        message_id (str | None): The message ID.

    Returns:
        ShortTermMemory: The created short term memory.

    Raises:
        Exception: If an error occurs.
    """

    if isinstance(value, dict):
        value = json.dumps(value)

    try:
        logger.info("Creating short term memory")
        stm = unique_sdk.ShortTermMemory.create(
            user_id=user_id,
            company_id=company_id,
            memoryName=key,
            chatId=chat_id,
            messageId=message_id,
            data=value,
        )
        return ShortTermMemory.model_validate(stm, by_alias=True, by_name=True)
    except Exception as e:
        logger.error(f"Error creating short term memory: {e}")
        raise e


def find_last_chat_memory(
    *,
    user_id: str,
    company_id: str,
    key: str,
    chat_id: str,
) -> ShortTermMemory:
    """
    Find the last chat short term memory.
    """
    stm = unique_sdk.ShortTermMemory.find_latest(
        user_id=user_id,
        company_id=company_id,
        memoryName=key,
        chatId=chat_id,
    )
    return ShortTermMemory.model_validate(stm, by_alias=True, by_name=True)


async def find_last_chat_memory_async(
    *,
    user_id: str,
    company_id: str,
    key: str,
    chat_id: str,
) -> ShortTermMemory:
    """
    Find the last chat short term memory.
    """
    stm = await unique_sdk.ShortTermMemory.find_latest_async(
        user_id=user_id,
        company_id=company_id,
        memoryName=key,
        chatId=chat_id,
    )
    return ShortTermMemory.model_validate(stm, by_alias=True, by_name=True)


def find_last_message_memory(
    *,
    user_id: str,
    company_id: str,
    key: str,
    message_id: str,
) -> ShortTermMemory:
    """
    Find the last message short term memory.
    """
    stm = unique_sdk.ShortTermMemory.find_latest(
        user_id=user_id,
        company_id=company_id,
        chatId=None,
        memoryName=key,
        messageId=message_id,
    )
    return ShortTermMemory.model_validate(stm, by_alias=True, by_name=True)


async def find_last_message_memory_async(
    *,
    user_id: str,
    company_id: str,
    key: str,
    message_id: str,
) -> ShortTermMemory:
    """
    Find the last message short term memory.
    """
    stm = await unique_sdk.ShortTermMemory.find_latest_async(
        user_id=user_id,
        company_id=company_id,
        chatId=None,
        memoryName=key,
        messageId=message_id,
    )
    return ShortTermMemory.model_validate(stm, by_alias=True, by_name=True)


def create_chat_memory(
    *,
    user_id: str,
    company_id: str,
    key: str,
    value: dict[str, Any] | str,
    chat_id: str,
) -> ShortTermMemory:
    """
    Create a chat short term memory.
    """
    stm = unique_sdk.ShortTermMemory.create(
        user_id=user_id,
        company_id=company_id,
        memoryName=key,
        chatId=chat_id,
        data=json.dumps(value) if isinstance(value, dict) else value,
    )
    return ShortTermMemory.model_validate(stm, by_alias=True, by_name=True)


async def create_chat_memory_async(
    *,
    user_id: str,
    company_id: str,
    key: str,
    value: dict[str, Any] | str,
    chat_id: str,
) -> ShortTermMemory:
    """
    Create a chat short term memory.
    """
    stm = await unique_sdk.ShortTermMemory.create_async(
        user_id=user_id,
        company_id=company_id,
        memoryName=key,
        chatId=chat_id,
        data=json.dumps(value) if isinstance(value, dict) else value,
    )
    return ShortTermMemory.model_validate(stm, by_alias=True, by_name=True)
