"""
Utility functions for Unique Custom Deep Research Engine

This module provides common utility functions for service access, configuration
handling, and other shared operations across the deep research workflow.
"""

from typing import Optional, Union

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

# Per-request counters for message log ordering - keyed by message_id
_request_counters: dict[str, int] = {}


def get_next_message_order(message_id: str) -> int:
    """
    Get the next message log order number for a specific request.

    Each message_id (request) gets its own counter: 1, 2, 3, 4, ...
    This ensures proper ordering within each request while avoiding
    race conditions between concurrent requests.

    Args:
        message_id: The message ID to get the next order for

    Returns:
        Next order number for this specific request
    """
    if message_id not in _request_counters:
        _request_counters[message_id] = 0

    _request_counters[message_id] += 1
    return _request_counters[message_id]


def cleanup_request_counter(message_id: str) -> None:
    """
    Clean up the counter for a completed request to prevent memory leaks.

    Should be called when a research request is completely finished.

    Args:
        message_id: The message ID to clean up
    """
    _request_counters.pop(message_id, None)


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
    text: Optional[str] = None,
    status: MessageLogStatus = MessageLogStatus.COMPLETED,
    details: Optional[MessageLogDetails] = None,
    uncited_references: Optional[MessageLogUncitedReferences] = None,
) -> None:
    """
    Create a message log entry with customizable details and references.

    Args:
        chat_service: ChatService instance for logging
        message_id: Message ID for the log entry
        text: Optional log message text (default: empty string)
        status: Log status (default: COMPLETED)
        details: Optional message details (default: empty)
        uncited_references: Optional uncited references (default: empty)
    """
    # Use per-request incrementing counter for clean, predictable ordering
    order = get_next_message_order(message_id)

    chat_service.create_message_log(
        message_id=message_id,
        text=text or "",
        status=status,
        order=order,
        details=details or MessageLogDetails(data=[]),
        uncited_references=uncited_references or MessageLogUncitedReferences(data=[]),
    )


def write_tool_message_log(
    config: RunnableConfig,
    text: Optional[str] = None,
    status: MessageLogStatus = MessageLogStatus.COMPLETED,
    details: Optional[MessageLogDetails] = None,
    uncited_references: Optional[MessageLogUncitedReferences] = None,
) -> None:
    """
    Write a tool message log entry using services from config.

    Args:
        config: RunnableConfig containing service instances
        text: Optional log message text (default: empty string)
        status: Log status (default: COMPLETED)
        details: Optional message details (default: empty)
        uncited_references: Optional uncited references (default: empty)
    """
    chat_service = get_chat_service_from_config(config)
    message_id = get_message_id_from_config(config)
    create_message_log_entry(
        chat_service, message_id, text, status, details, uncited_references
    )


def write_state_message_log(
    state: Union[CustomAgentState, CustomSupervisorState, CustomResearcherState],
    text: Optional[str] = None,
    status: MessageLogStatus = MessageLogStatus.COMPLETED,
    details: Optional[MessageLogDetails] = None,
    uncited_references: Optional[MessageLogUncitedReferences] = None,
) -> None:
    """
    Write a message log entry using services from state.

    Args:
        state: State containing ChatService and message_id
        text: Optional log message text (default: empty string)
        status: Log status (default: COMPLETED)
        details: Optional message details (default: empty)
        uncited_references: Optional uncited references (default: empty)
    """
    chat_service = state["chat_service"]
    message_id = state["message_id"]

    # Use the same per-request counter as all other message logging
    order = get_next_message_order(message_id)

    chat_service.create_message_log(
        message_id=message_id,
        text=text or "",
        status=status,
        order=order,
        details=details or MessageLogDetails(data=[]),
        uncited_references=uncited_references or MessageLogUncitedReferences(data=[]),
    )
