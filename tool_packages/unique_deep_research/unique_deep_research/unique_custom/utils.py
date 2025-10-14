"""
Utility functions for Unique Custom Deep Research Engine

This module provides common utility functions for service access, configuration
handling, and other shared operations across the deep research workflow.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

import tiktoken
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    MessageLikeRepresentation,
    ToolMessage,
    filter_messages,
)
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import BaseTool
from unique_toolkit.chat.schemas import (
    MessageLogDetails,
    MessageLogStatus,
    MessageLogUncitedReferences,
)
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model.infos import LanguageModelInfo

from ..config import BaseEngine
from .citation import GlobalCitationManager
from .state import AgentState, ResearcherState, SupervisorState

_LOGGER = logging.getLogger(__name__)


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


def get_engine_config(config: RunnableConfig) -> BaseEngine:
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

    custom_config = config["configurable"].get("engine_config")
    if not custom_config:
        raise KeyError("custom_engine_config missing from RunnableConfig")

    if not isinstance(custom_config, BaseEngine):
        raise TypeError(
            f"engine_config is {type(custom_config)}, expected DeepResearchToolConfig"
        )

    return custom_config


def get_citation_manager(config: RunnableConfig) -> GlobalCitationManager:
    """
    Extract GlobalCitationManager from RunnableConfig.

    The citation manager is provided by the service layer and shared
    across all subgraphs to enable centralized citation tracking.

    Args:
        config: LangChain RunnableConfig containing citation manager

    Returns:
        GlobalCitationManager instance (guaranteed to exist)

    Raises:
        KeyError: If citation_manager is missing (indicates system error)
        TypeError: If citation_manager is wrong type (indicates system error)
    """
    if not config or "configurable" not in config:
        raise KeyError("RunnableConfig missing 'configurable' section")

    citation_manager = config["configurable"].get("citation_manager")
    if not citation_manager:
        raise KeyError("citation_manager missing from RunnableConfig")

    if not isinstance(citation_manager, GlobalCitationManager):
        raise TypeError(
            f"citation_manager is {type(citation_manager)}, expected GlobalCitationManager"
        )

    return citation_manager


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
    state: Union[AgentState, SupervisorState, ResearcherState],
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


# Tool execution utilities (temporary file - will be merged into utils.py)


async def execute_tool_safely(
    tool: BaseTool, args: Dict[str, Any], config: RunnableConfig
) -> str:
    """
    Safely execute a tool with error handling and token limit awareness.

    Args:
        tool: The tool to execute (typically a LangChain tool)
        args: Arguments to pass to the tool
        config: Runtime configuration for the tool execution

    Returns:
        Tool execution result as a string, or error message if execution fails

    Prevents tool execution errors from crashing the workflow.
    Returns error messages as strings that can be processed by the agent.
    """
    try:
        return await tool.ainvoke(args, config)
    except Exception as e:
        tool_name = getattr(tool, "name", str(tool))

        # Handle token limit errors specifically
        if is_token_error(e):
            _LOGGER.warning(f"Token limit exceeded in tool {tool_name}: {str(e)}")
            return f"Tool {tool_name} failed due to token limit: {str(e)}"
        else:
            _LOGGER.error(f"Error executing tool {tool_name}: {str(e)}")
            return f"Error executing tool {tool_name}: {str(e)}"


# Token management utilities


def is_token_error(exception: Exception) -> bool:
    """Simple check if exception is token-related."""
    error_str = str(exception).lower()
    return any(
        pattern in error_str
        for pattern in [
            "token limit",
            "context length",
            "prompt is too long",
            "input too long",
            "maximum context",
            "context_length_exceeded",
            "invalid_request_error",
        ]
    )


def get_notes_from_tool_calls(messages: List[MessageLikeRepresentation]) -> List[str]:
    """
    Extract notes from tool call messages.

    This function filters messages to find tool messages and extracts their content
    as notes, following the pattern from open_deep_research.

    Args:
        messages: List of messages to extract tool call content from

    Returns:
        List of strings containing tool call content
    """
    return [
        str(tool_msg.content)
        for tool_msg in filter_messages(messages, include_types=["tool"])
    ]


def count_tokens(text: str, model_info: LanguageModelInfo) -> int:
    """Count tokens in text using the model's encoder."""
    if not text:
        return 0
    try:
        encoder = tiktoken.get_encoding(model_info.encoder_name)
        return len(encoder.encode(text))
    except Exception as e:
        _LOGGER.warning(f"Error counting tokens: {e}")
        return len(str(text)) // 4  # Rough fallback


def count_message_tokens(message: BaseMessage, model_info: LanguageModelInfo) -> int:
    """Count tokens in a message including content, tool calls, and tool responses."""
    total_tokens = 4  # Base overhead per message

    # Count content
    if message.content:
        total_tokens += count_tokens(str(message.content), model_info)

    # Count tool calls (AIMessage with tool_calls)
    if isinstance(message, AIMessage) and message.tool_calls:
        for tool_call in message.tool_calls:
            # Count tool name and arguments
            if isinstance(tool_call, dict):
                total_tokens += count_tokens(str(tool_call), model_info)
            else:
                total_tokens += count_tokens(str(tool_call), model_info)
            total_tokens += 4  # Base overhead per tool call

    return total_tokens


def prepare_messages_for_model(
    messages: List[BaseMessage],
    model_info: LanguageModelInfo,
) -> List[BaseMessage]:
    """
    Smart message filtering that keeps first two messages (system + initial task) and recent messages.
    Ensures tool messages are not orphaned from their AI message calls.

    Args:
        messages: List of messages to prepare
        model_info: Model information with token limits

    Returns:
        List of messages that fit within token limit ratio
    """
    if not messages:
        return messages

    if len(messages) <= 2:
        return messages

    # Use specified ratio of input limit to leave buffer
    token_budget = model_info.token_limits.token_limit_input

    # Always keep first two messages (system + initial task)
    system_msg = messages[0]
    first_msg = messages[1]
    other_messages = messages[2:]

    # Count tokens for messages we always keep
    system_tokens = count_message_tokens(system_msg, model_info)
    first_msg_tokens = count_message_tokens(first_msg, model_info)

    # Reserve tokens for truncation message if needed
    truncation_msg_tokens = 50  # Approximate tokens for truncation notice

    # Calculate remaining budget
    remaining_budget = (
        token_budget - system_tokens - first_msg_tokens - truncation_msg_tokens
    )

    # Keep most recent messages that fit
    message_subset = []
    total_tokens = 0

    for message in reversed(other_messages):
        msg_tokens = count_message_tokens(message, model_info)
        if total_tokens + msg_tokens <= remaining_budget:
            message_subset.insert(0, message)
            total_tokens += msg_tokens
        else:
            break

    # Remove orphaned tool messages at the start (tool messages without their AI message)
    # Tool messages should always come after an AI message with tool_calls
    while message_subset and isinstance(message_subset[0], ToolMessage):
        _LOGGER.info("Removing orphaned tool message at start of context")
        message_subset.pop(0)

    # Build final message list
    final_messages = [system_msg, first_msg]

    # Add truncation notice if we removed messages
    if len(message_subset) < len(other_messages):
        truncation_notice = AIMessage(
            content="[Previous conversation history truncated to fit context window]"
        )
        final_messages.append(truncation_notice)
        _LOGGER.info(
            f"Trimmed {len(other_messages) - len(message_subset)} messages from middle of conversation"
        )

    final_messages.extend(message_subset)
    return final_messages


def remove_up_to_last_ai_message(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Truncate message history by removing middle messages, keeping first two and most recent.

    Keeps:
    - First message (system)
    - Second message (initial task)
    - Adds truncation notice
    - Removes everything up to the last AI message

    Args:
        messages: List of message objects to truncate

    Returns:
        Truncated message list with first two messages + truncation notice and from last AI message and up
    """
    if len(messages) <= 2:
        return messages

    # Keep first two messages (system + initial task)
    # Add truncation notice as AI message
    truncation_notice = AIMessage(
        content="[Conversation history truncated due to token limits - retrying with minimal context]"
    )
    message_subset = []
    # Search backwards through messages to find the last AI message
    for i in range(len(messages) - 1, -1, -1):
        message_subset.insert(0, messages[i])
        if isinstance(messages[i], AIMessage):
            # Return everything up to (but not including) the last AI message
            break
    if len(message_subset) == len(messages) + 2:
        return messages

    # Keep first two messages (system + initial task) and truncation notice with middle messages removed
    return [messages[0], messages[1], truncation_notice] + message_subset


async def ainvoke_with_token_handling(
    model: Runnable[List[BaseMessage], Any],
    messages: List[BaseMessage],
    model_info: LanguageModelInfo,
) -> Any:
    """
    Invoke model with proactive token filtering and retry logic with exponential backoff.

    Handles token limit errors by progressively truncating message history.

    Args:
        model: The model to invoke
        messages: List of messages to send
        model_info: Model info for token limits

    Returns:
        Model response
    """
    # Prepare messages with token filtering
    prepared_messages = prepare_messages_for_model(messages, model_info)

    # Retry configuration
    max_retries = 3
    base_delay = 4.0  # Base delay in seconds

    for attempt in range(max_retries + 1):
        try:
            return await model.ainvoke(prepared_messages)
        except Exception as e:
            # Handle token errors by truncating history and retrying
            if is_token_error(e):
                # Filtering is not perfect, so in unlikely case we need to truncate the message history to the last AI message
                _LOGGER.warning(
                    f"Token limit error: {str(e)}. Truncating message history to last AI message and retrying..."
                )
                messages = remove_up_to_last_ai_message(messages)
                prepared_messages = prepare_messages_for_model(messages, model_info)
                continue

            # For other errors, retry with exponential backoff
            if attempt < max_retries:
                delay = base_delay * (2**attempt)  # Exponential backoff: 4s, 8s, 16s
                _LOGGER.warning(
                    f"Model invocation failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}. Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                _LOGGER.error(
                    f"Model invocation failed after {max_retries + 1} attempts: {str(e)}"
                )
                raise e
