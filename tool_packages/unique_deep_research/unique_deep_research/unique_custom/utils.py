"""
Utility functions for Unique Custom Deep Research Engine

This module provides common utility functions for service access, configuration
handling, and other shared operations across the deep research workflow.
"""

import time
from typing import Tuple, Union

from langchain_core.runnables import RunnableConfig
from unique_toolkit.chat.schemas import (
    MessageLogDetails,
    MessageLogStatus,
    MessageLogUncitedReferences,
)
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.service import ContentService

from ..config import UniqueCustomEngineConfig
from .state import CustomAgentState, CustomResearcherState, CustomSupervisorState


class ServiceAccessError(Exception):
    """Raised when a required service is not available or invalid."""

    pass


def get_chat_service_from_config(config: RunnableConfig) -> ChatService:
    """
    Extract ChatService from RunnableConfig.

    The ChatService is always provided by the service layer, so this
    function assumes it exists and will fail fast if not found.

    Args:
        config: LangChain RunnableConfig containing service instances

    Returns:
        ChatService instance (guaranteed to exist)

    Raises:
        KeyError: If ChatService is missing (indicates system error)
        TypeError: If ChatService is wrong type (indicates system error)
    """
    if not config or "configurable" not in config:
        raise KeyError("RunnableConfig missing 'configurable' section")

    configurable = config.get("configurable", {})
    chat_service = configurable.get("chat_service")

    if not chat_service:
        raise KeyError("chat_service missing from RunnableConfig")

    if not isinstance(chat_service, ChatService):
        raise TypeError(f"chat_service is {type(chat_service)}, expected ChatService")

    return chat_service


def get_content_service_from_config(config: RunnableConfig) -> ContentService:
    """
    Extract ContentService from RunnableConfig.

    The ContentService is always provided by the service layer, so this
    function assumes it exists and will fail fast if not found.

    Args:
        config: LangChain RunnableConfig containing service instances

    Returns:
        ContentService instance (guaranteed to exist)

    Raises:
        KeyError: If ContentService is missing (indicates system error)
        TypeError: If ContentService is wrong type (indicates system error)
    """
    if not config or "configurable" not in config:
        raise KeyError("RunnableConfig missing 'configurable' section")

    configurable = config.get("configurable", {})
    content_service = configurable.get("content_service")

    if not content_service:
        raise KeyError("content_service missing from RunnableConfig")

    if not isinstance(content_service, ContentService):
        raise TypeError(
            f"content_service is {type(content_service)}, expected ContentService"
        )

    return content_service


# get_required_content_service is now redundant - get_content_service_from_config always returns a valid service


def get_message_id_from_config(config: RunnableConfig) -> str:
    """
    Extract message_id from RunnableConfig.

    The message_id is always provided by the service layer, so this
    function assumes it exists and will fail fast if not found.

    Args:
        config: LangChain RunnableConfig containing configuration

    Returns:
        Message ID string (guaranteed to exist)

    Raises:
        KeyError: If message_id is missing (indicates system error)
    """
    if not config or "configurable" not in config:
        raise KeyError("RunnableConfig missing 'configurable' section")

    configurable = config.get("configurable", {})
    message_id = configurable.get("message_id")

    if not message_id:
        raise KeyError("message_id missing from RunnableConfig")

    return str(message_id)


def get_custom_engine_config(config: RunnableConfig) -> UniqueCustomEngineConfig:
    """
    Extract custom engine configuration from RunnableConfig.

    The configuration is always provided by the service layer, so this
    function assumes it exists and will fail fast if not found.

    Args:
        config: LangChain RunnableConfig containing configuration

    Returns:
        UniqueCustomEngineConfig instance (guaranteed to exist)

    Raises:
        KeyError: If configuration is missing (indicates system error)
        TypeError: If configuration is wrong type (indicates system error)
    """
    if not config or "configurable" not in config:
        raise KeyError("RunnableConfig missing 'configurable' section")

    custom_config = config["configurable"].get("custom_engine_config")
    if not custom_config:
        raise KeyError("custom_engine_config missing from RunnableConfig")

    if not isinstance(custom_config, UniqueCustomEngineConfig):
        raise TypeError(
            f"custom_engine_config is {type(custom_config)}, expected UniqueCustomEngineConfig"
        )

    return custom_config


def create_message_log_entry(
    chat_service: ChatService,
    message_id: str,
    text: str,
    status: MessageLogStatus = MessageLogStatus.COMPLETED,
) -> None:
    """
    Create a message log entry with standardized formatting.

    Args:
        chat_service: ChatService instance for logging
        message_id: Message ID for the log entry
        text: Log message text
        status: Log status (default: COMPLETED)
    """
    # Generate a timestamp-based order for thread-safe logging
    order = int(time.time() * 1000) % 1000000

    chat_service.create_message_log(
        message_id=message_id,
        text=text,
        status=status,
        order=order,
        details=MessageLogDetails(data=[]),
        uncited_references=MessageLogUncitedReferences(data=[]),
    )


def write_tool_message_log(
    config: RunnableConfig,
    text: str,
    status: MessageLogStatus = MessageLogStatus.COMPLETED,
) -> None:
    """
    Write a tool message log entry using services from config.

    Args:
        config: RunnableConfig containing service instances
        text: Log message text
        status: Log status (default: COMPLETED)
    """
    chat_service = get_chat_service_from_config(config)
    message_id = get_message_id_from_config(config)
    create_message_log_entry(chat_service, message_id, text, status)


def get_and_increment_message_log_idx(
    state: Union[CustomAgentState, CustomSupervisorState, CustomResearcherState],
) -> int:
    """
    Get current message log index and increment it atomically.

    Args:
        state: State dictionary containing message_log_idx

    Returns:
        Current message log index before increment
    """
    idx = state.get("message_log_idx", 0)
    state["message_log_idx"] = idx + 1
    return idx


def write_state_message_log(
    state: Union[CustomAgentState, CustomSupervisorState, CustomResearcherState],
    text: str,
    status: MessageLogStatus = MessageLogStatus.COMPLETED,
) -> None:
    """
    Write a message log entry using services from state.

    Args:
        state: State containing ChatService and message_id
        text: Log message text
        status: Log status (default: COMPLETED)
    """
    chat_service = state["chat_service"]
    message_id = state["message_id"]

    order = get_and_increment_message_log_idx(state)

    chat_service.create_message_log(
        message_id=message_id,
        text=text,
        status=status,
        order=order,
        details=MessageLogDetails(data=[]),
        uncited_references=MessageLogUncitedReferences(data=[]),
    )


def safe_content_operation(
    config: RunnableConfig,
    operation_name: str,
    fallback_message: str = "Content operation failed",
) -> Tuple[ContentService, str]:
    """
    Get ContentService for an operation with logging.

    Since ContentService is always provided, this function primarily
    handles logging and error formatting.

    Args:
        config: RunnableConfig containing services
        operation_name: Name of the operation for logging
        fallback_message: Message to use in error formatting

    Returns:
        Tuple of (ContentService, empty string for success)

    Raises:
        KeyError/TypeError: If ContentService is missing or invalid (system error)
    """
    write_tool_message_log(config, f"Starting {operation_name}...")

    try:
        content_service = get_content_service_from_config(config)
        return content_service, ""
    except (KeyError, TypeError) as e:
        error_msg = f"{fallback_message}: {str(e)}"
        write_tool_message_log(config, error_msg, MessageLogStatus.FAILED)
        raise  # Re-raise the exception since this indicates a system error
