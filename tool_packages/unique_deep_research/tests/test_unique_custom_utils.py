"""
Unit tests for unique_custom/utils.py module.
"""

from typing import Any, List, cast
from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model.infos import LanguageModelInfo

from unique_deep_research.config import UniqueEngine
from unique_deep_research.unique_custom.utils import (
    ainvoke_with_token_handling,
    cleanup_request_counter,
    count_message_tokens,
    count_tokens,
    create_message_log_entry,
    execute_tool_safely,
    get_chat_service_from_config,
    get_content_service_from_config,
    get_engine_config,
    get_next_message_order,
    get_notes_from_tool_calls,
    is_token_error,
    prepare_messages_for_model,
    remove_up_to_last_ai_message,
    write_state_message_log,
    write_tool_message_log,
)


@pytest.mark.ai
def test_get_next_message_order__increments_counter__for_same_message_id() -> None:
    """
    Purpose: Verify get_next_message_order increments counter for same message_id.
    Why this matters: Ensures proper ordering of message logs within each request.
    Setup summary: Call function multiple times with same message_id and verify increment.
    """
    # Arrange
    message_id = "test-message-123-unique"

    # Act
    order1 = get_next_message_order(message_id)
    order2 = get_next_message_order(message_id)
    order3 = get_next_message_order(message_id)

    # Assert
    assert order1 == 1
    assert order2 == 2
    assert order3 == 3


@pytest.mark.ai
def test_get_next_message_order__maintains_separate_counters__for_different_message_ids() -> (
    None
):
    """
    Purpose: Verify get_next_message_order maintains separate counters for different message_ids.
    Why this matters: Prevents interference between concurrent requests.
    Setup summary: Call function with different message_ids and verify separate counters.
    """
    # Arrange
    message_id1 = "test-message-1"
    message_id2 = "test-message-2"

    # Act
    order1a = get_next_message_order(message_id1)
    order2a = get_next_message_order(message_id2)
    order1b = get_next_message_order(message_id1)
    order2b = get_next_message_order(message_id2)

    # Assert
    assert order1a == 1
    assert order2a == 1
    assert order1b == 2
    assert order2b == 2


@pytest.mark.ai
def test_cleanup_request_counter__removes_counter__for_specific_message_id() -> None:
    """
    Purpose: Verify cleanup_request_counter removes counter for specific message_id.
    Why this matters: Allows cleanup of request-specific counters after completion.
    Setup summary: Create counter, cleanup, and verify it's removed.
    """
    # Arrange
    message_id = "test-message-cleanup"
    get_next_message_order(message_id)  # Create counter

    # Act
    cleanup_request_counter(message_id)

    # Assert
    # Next call should start from 1 again
    order = get_next_message_order(message_id)
    assert order == 1


@pytest.mark.ai
def test_cleanup_request_counter__handles_nonexistent_message_id__gracefully() -> None:
    """
    Purpose: Verify cleanup_request_counter handles nonexistent message_id gracefully.
    Why this matters: Ensures robust cleanup without errors for non-existent counters.
    Setup summary: Call cleanup on non-existent message_id and verify no error.
    """
    # Arrange
    nonexistent_id = "nonexistent-message-id"

    # Act & Assert - Should not raise exception
    cleanup_request_counter(nonexistent_id)


@pytest.mark.ai
def test_get_chat_service_from_config__returns_chat_service__from_config() -> None:
    """
    Purpose: Verify get_chat_service_from_config returns chat service from config.
    Why this matters: Provides access to chat service for message logging.
    Setup summary: Create config with chat service and verify retrieval.
    """
    # Arrange
    mock_chat_service = Mock(spec=ChatService)
    config = {"configurable": {"chat_service": mock_chat_service}}

    # Act
    result = get_chat_service_from_config(cast(Any, config))

    # Assert
    assert result == mock_chat_service


@pytest.mark.ai
def test_get_chat_service_from_config__raises_error__when_service_missing() -> None:
    """
    Purpose: Verify get_chat_service_from_config raises error when service missing.
    Why this matters: Ensures proper error handling when required service is not available.
    Setup summary: Create config without chat service and verify error is raised.
    """
    # Arrange
    config = cast(Any, {"configurable": {}})

    # Act & Assert
    with pytest.raises(KeyError, match="chat_service missing from RunnableConfig"):
        get_chat_service_from_config(config)


@pytest.mark.ai
def test_get_content_service_from_config__returns_content_service__from_config() -> (
    None
):
    """
    Purpose: Verify get_content_service_from_config returns content service from config.
    Why this matters: Provides access to content service for content operations.
    Setup summary: Create config with content service and verify retrieval.
    """
    # Arrange
    mock_content_service = Mock(spec=ContentService)
    config = {"configurable": {"content_service": mock_content_service}}

    # Act
    result = get_content_service_from_config(cast(Any, config))

    # Assert
    assert result == mock_content_service


@pytest.mark.ai
def test_get_content_service_from_config__raises_error__when_service_missing() -> None:
    """
    Purpose: Verify get_content_service_from_config raises error when service missing.
    Why this matters: Ensures proper error handling when required service is not available.
    Setup summary: Create config without content service and verify error is raised.
    """
    # Arrange
    config = {"configurable": {}}

    # Act & Assert
    with pytest.raises(KeyError, match="content_service missing from RunnableConfig"):
        get_content_service_from_config(cast(Any, config))


@pytest.mark.ai
def test_get_engine_config__returns_engine_config__from_config() -> None:
    """
    Purpose: Verify get_engine_config returns engine config from config.
    Why this matters: Provides access to engine configuration for research operations.
    Setup summary: Create config with engine config and verify retrieval.
    """
    # Arrange
    mock_engine_config = Mock(spec=UniqueEngine)
    config = {"configurable": {"engine_config": mock_engine_config}}

    # Act
    result = get_engine_config(cast(Any, config))

    # Assert
    assert result == mock_engine_config


@pytest.mark.ai
def test_get_engine_config__raises_error__when_config_missing() -> None:
    """
    Purpose: Verify get_engine_config raises error when config missing.
    Why this matters: Ensures proper error handling when required config is not available.
    Setup summary: Create config without engine config and verify error is raised.
    """
    # Arrange
    config = {"configurable": {}}

    # Act & Assert
    with pytest.raises(KeyError, match="engine_config missing from RunnableConfig"):
        get_engine_config(cast(Any, config))


@pytest.mark.ai
async def test_execute_tool_safely__returns_result__when_tool_succeeds() -> None:
    """
    Purpose: Verify execute_tool_safely returns result when tool succeeds.
    Why this matters: Provides safe tool execution with error handling.
    Setup summary: Mock successful tool execution and verify result is returned.
    """
    # Arrange
    mock_tool = Mock()
    mock_tool.ainvoke = AsyncMock(return_value="success")
    args = {"test": "args"}
    config = {"config": "test"}

    # Act
    result = await execute_tool_safely(mock_tool, args, cast(Any, config))

    # Assert
    assert result == "success"
    mock_tool.ainvoke.assert_called_once_with(args, config)


@pytest.mark.ai
async def test_execute_tool_safely__returns_error_message__when_tool_fails() -> None:
    """
    Purpose: Verify execute_tool_safely returns error message when tool fails.
    Why this matters: Ensures graceful handling of tool execution failures.
    Setup summary: Mock failing tool execution and verify error message is returned.
    """
    # Arrange
    mock_tool = Mock()
    mock_tool.ainvoke = AsyncMock(side_effect=Exception("Tool failed"))
    args = {"test": "args"}
    config = {"config": "test"}

    # Act
    result = await execute_tool_safely(mock_tool, args, cast(Any, config))

    # Assert
    assert "Tool failed" in result
    assert "Error executing tool" in result


@pytest.mark.ai
def test_write_state_message_log__calls_chat_service__with_correct_parameters() -> None:
    """
    Purpose: Verify write_state_message_log calls chat service with correct parameters.
    Why this matters: Ensures proper message logging in LangGraph state.
    Setup summary: Mock state with chat service and verify correct parameters are passed.
    """
    # Arrange
    mock_chat_service = Mock(spec=ChatService)
    mock_chat_service.create_message_log = Mock()
    state = cast(
        Any,
        {
            "chat_service": mock_chat_service,
            "message_id": "test-message",
        },
    )
    text = "Test log message"

    # Act
    write_state_message_log(state, text)

    # Assert
    mock_chat_service.create_message_log.assert_called_once()
    call_args = mock_chat_service.create_message_log.call_args
    assert call_args[1]["message_id"] == "test-message"
    assert call_args[1]["text"] == text


@pytest.mark.ai
def test_write_tool_message_log__calls_chat_service__with_tool_specific_parameters() -> (
    None
):
    """
    Purpose: Verify write_tool_message_log calls chat service with tool-specific parameters.
    Why this matters: Ensures proper tool message logging with correct status.
    Setup summary: Mock config with chat service and verify tool-specific parameters are passed.
    """
    # Arrange
    mock_chat_service = Mock(spec=ChatService)
    mock_chat_service.create_message_log = Mock()
    config = cast(
        Any,
        {
            "configurable": {
                "chat_service": mock_chat_service,
                "message_id": "test-message",
            }
        },
    )
    text = "Tool execution message"

    # Act
    write_tool_message_log(config, text)

    # Assert
    mock_chat_service.create_message_log.assert_called_once()
    call_args = mock_chat_service.create_message_log.call_args
    assert call_args[1]["message_id"] == "test-message"
    assert call_args[1]["text"] == text


@pytest.mark.ai
def test_create_message_log_entry__calls_chat_service__with_complete_parameters() -> (
    None
):
    """
    Purpose: Verify create_message_log_entry calls chat service with complete parameters.
    Why this matters: Ensures comprehensive message logging with all required fields.
    Setup summary: Mock chat service and verify all parameters are passed correctly.
    """
    # Arrange
    mock_chat_service = Mock(spec=ChatService)
    mock_chat_service.create_message_log = Mock()
    message_id = "test-message"
    text = "Complete log message"

    # Act
    create_message_log_entry(mock_chat_service, message_id, text)

    # Assert
    mock_chat_service.create_message_log.assert_called_once()
    call_args = mock_chat_service.create_message_log.call_args
    assert call_args[1]["message_id"] == message_id
    assert call_args[1]["text"] == text
    assert "status" in call_args[1]
    assert "details" in call_args[1]
    assert "uncited_references" in call_args[1]


def test_is_token_error__returns_true__for_token_related_errors() -> None:
    """
    Purpose: Verify is_token_error returns true for token-related error messages.
    Why this matters: Enables proper handling of token limit errors in tool execution.
    Setup summary: Test various token error patterns and verify detection.
    """
    # Arrange
    token_errors = [
        Exception("token limit exceeded"),
        Exception("context length exceeded"),
        Exception("prompt is too long"),
        Exception("input too long"),
        Exception("maximum context reached"),
        Exception("context_length_exceeded"),
        Exception("invalid_request_error"),
    ]

    # Act & Assert
    for error in token_errors:
        assert is_token_error(error) is True


@pytest.mark.ai
def test_is_token_error__returns_false__for_non_token_errors() -> None:
    """
    Purpose: Verify is_token_error returns false for non-token-related errors.
    Why this matters: Ensures only token errors are identified as such.
    Setup summary: Test non-token error patterns and verify they are not detected.
    """
    # Arrange
    non_token_errors = [
        Exception("network error"),
        Exception("authentication failed"),
        Exception("invalid input"),
        Exception("permission denied"),
    ]

    # Act & Assert
    for error in non_token_errors:
        assert is_token_error(error) is False


@pytest.mark.ai
def test_get_notes_from_tool_calls__extracts_tool_messages__from_mixed_messages() -> (
    None
):
    """
    Purpose: Verify get_notes_from_tool_calls extracts tool messages from mixed message list.
    Why this matters: Enables extraction of tool call results for processing.
    Setup summary: Create mixed message list with tool messages and verify extraction.
    """
    # Arrange
    messages = [
        HumanMessage(content="Hello"),
        AIMessage(content="I'll help you"),
        ToolMessage(content="Tool result 1", tool_call_id="call1"),
        AIMessage(content="Let me try another tool"),
        ToolMessage(content="Tool result 2", tool_call_id="call2"),
    ]

    # Act
    notes = get_notes_from_tool_calls(messages)

    # Assert
    assert len(notes) == 2
    assert "Tool result 1" in notes
    assert "Tool result 2" in notes


@pytest.mark.ai
def test_get_notes_from_tool_calls__returns_empty_list__when_no_tool_messages() -> None:
    """
    Purpose: Verify get_notes_from_tool_calls returns empty list when no tool messages exist.
    Why this matters: Ensures graceful handling when no tool calls are present.
    Setup summary: Create message list without tool messages and verify empty result.
    """
    # Arrange
    messages = [
        HumanMessage(content="Hello"),
        AIMessage(content="I'll help you"),
    ]

    # Act
    notes = get_notes_from_tool_calls(messages)

    # Assert
    assert notes == []


@pytest.mark.ai
@patch("unique_deep_research.unique_custom.utils.tiktoken.get_encoding")
def test_count_tokens__returns_token_count__for_valid_text(mock_get_encoding) -> None:
    """
    Purpose: Verify count_tokens returns correct token count for valid text.
    Why this matters: Enables accurate token counting for model input limits.
    Setup summary: Mock tiktoken encoder and verify token counting.
    """
    # Arrange
    mock_encoder = Mock()
    mock_encoder.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens
    mock_get_encoding.return_value = mock_encoder
    model_info = Mock(spec=LanguageModelInfo)
    model_info.encoder_name = "cl100k_base"
    text = "Hello world"

    # Act
    count = count_tokens(text, model_info)

    # Assert
    assert count == 5
    mock_get_encoding.assert_called_once_with("cl100k_base")
    mock_encoder.encode.assert_called_once_with(text)


@pytest.mark.ai
@patch("unique_deep_research.unique_custom.utils.tiktoken.get_encoding")
def test_count_tokens__returns_zero__for_empty_text(mock_get_encoding) -> None:
    """
    Purpose: Verify count_tokens returns zero for empty text.
    Why this matters: Ensures proper handling of empty input.
    Setup summary: Test with empty text and verify zero count.
    """
    # Arrange
    model_info = Mock(spec=LanguageModelInfo)
    model_info.encoder_name = "cl100k_base"

    # Act
    count = count_tokens("", model_info)

    # Assert
    assert count == 0
    mock_get_encoding.assert_not_called()


@pytest.mark.ai
@patch("unique_deep_research.unique_custom.utils.tiktoken.get_encoding")
def test_count_tokens__returns_fallback__when_encoding_fails(mock_get_encoding) -> None:
    """
    Purpose: Verify count_tokens returns fallback count when encoding fails.
    Why this matters: Ensures graceful handling of encoding errors.
    Setup summary: Mock encoding failure and verify fallback calculation.
    """
    # Arrange
    mock_get_encoding.side_effect = Exception("Encoding error")
    model_info = Mock(spec=LanguageModelInfo)
    model_info.encoder_name = "cl100k_base"
    text = "Hello world"  # 11 characters

    # Act
    count = count_tokens(text, model_info)

    # Assert
    assert count == 2  # 11 // 4 = 2 (rough fallback)


@pytest.mark.ai
@patch("unique_deep_research.unique_custom.utils.count_tokens")
def test_count_message_tokens__counts_content_and_tool_calls(mock_count_tokens) -> None:
    """
    Purpose: Verify count_message_tokens counts content and tool calls correctly.
    Why this matters: Enables accurate token counting for complex messages.
    Setup summary: Mock count_tokens and verify message token calculation.
    """
    # Arrange
    mock_count_tokens.side_effect = [10, 5, 3]  # content, tool_call1, tool_call2
    model_info = Mock(spec=LanguageModelInfo)
    message = AIMessage(
        content="Hello",
        tool_calls=[
            {"id": "call1", "name": "tool1", "args": {"arg": "value"}},
            {"id": "call2", "name": "tool2", "args": {"arg": "value"}},
        ],
    )

    # Act
    count = count_message_tokens(message, model_info)

    # Assert
    # Base overhead (4) + content (10) + tool_call1 (5 + 4) + tool_call2 (3 + 4) = 30
    assert count == 30
    assert mock_count_tokens.call_count == 3


@pytest.mark.ai
@patch("unique_deep_research.unique_custom.utils.count_tokens")
def test_count_message_tokens__counts_content_only__for_simple_message(
    mock_count_tokens,
) -> None:
    """
    Purpose: Verify count_message_tokens counts content only for simple messages.
    Why this matters: Ensures proper token counting for messages without tool calls.
    Setup summary: Mock count_tokens and verify simple message token calculation.
    """
    # Arrange
    mock_count_tokens.return_value = 5
    model_info = Mock(spec=LanguageModelInfo)
    message = HumanMessage(content="Hello")

    # Act
    count = count_message_tokens(message, model_info)

    # Assert
    # Base overhead (4) + content (5) = 9
    assert count == 9
    mock_count_tokens.assert_called_once_with("Hello", model_info)


@pytest.mark.ai
@patch("unique_deep_research.unique_custom.utils.count_message_tokens")
def test_prepare_messages_for_model__returns_original__for_short_message_list(
    mock_count_message_tokens,
) -> None:
    """
    Purpose: Verify prepare_messages_for_model returns original list for short message lists.
    Why this matters: Ensures no unnecessary processing for small message lists.
    Setup summary: Mock token counting and verify short list handling.
    """
    # Arrange
    mock_count_message_tokens.return_value = 10
    model_info = Mock(spec=LanguageModelInfo)
    mock_token_limits = Mock()
    mock_token_limits.token_limit_input = 1000
    model_info.token_limits = mock_token_limits
    messages = [
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there"),
    ]

    # Act
    result = prepare_messages_for_model(messages, model_info)

    # Assert
    assert result == messages
    assert len(result) == 2


@pytest.mark.ai
@patch("unique_deep_research.unique_custom.utils.count_message_tokens")
def test_prepare_messages_for_model__truncates_messages__when_over_limit(
    mock_count_message_tokens,
) -> None:
    """
    Purpose: Verify prepare_messages_for_model truncates messages when over token limit.
    Why this matters: Ensures messages fit within model token limits.
    Setup summary: Mock token counting to exceed limit and verify truncation.
    """
    # Arrange
    # System (50) + first (50) + truncation (50) + remaining budget = 100
    # Each additional message = 200 tokens (exceeds budget)
    mock_count_message_tokens.side_effect = [50, 50, 200, 200, 200]
    model_info = Mock(spec=LanguageModelInfo)
    mock_token_limits = Mock()
    mock_token_limits.token_limit_input = 200
    model_info.token_limits = mock_token_limits
    messages = [
        HumanMessage(content="System message"),
        AIMessage(content="First message"),
        HumanMessage(content="Message 1"),
        HumanMessage(content="Message 2"),
        HumanMessage(content="Message 3"),
    ]

    # Act
    result = prepare_messages_for_model(messages, model_info)

    # Assert
    assert len(result) == 3  # System + First + Truncation notice
    assert "truncated" in str(result[2].content).lower()


@pytest.mark.ai
def test_remove_up_to_last_ai_message__returns_original__for_short_list() -> None:
    """
    Purpose: Verify remove_up_to_last_ai_message returns original list for short message lists.
    Why this matters: Ensures no unnecessary processing for small message lists.
    Setup summary: Test with short message list and verify no changes.
    """
    # Arrange
    messages = [
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there"),
    ]

    # Act
    result = remove_up_to_last_ai_message(messages)

    # Assert
    assert result == messages


@pytest.mark.ai
def test_remove_up_to_last_ai_message__truncates_to_last_ai_message() -> None:
    """
    Purpose: Verify remove_up_to_last_ai_message truncates to last AI message.
    Why this matters: Ensures proper message history truncation for token limits.
    Setup summary: Create long message list and verify truncation to last AI message.
    """
    # Arrange
    messages = [
        HumanMessage(content="System message"),
        AIMessage(content="First AI message"),
        HumanMessage(content="User message 1"),
        HumanMessage(content="User message 2"),
        AIMessage(content="Last AI message"),
        HumanMessage(content="Final user message"),
    ]

    # Act
    result = remove_up_to_last_ai_message(messages)

    # Assert
    assert len(result) == 5  # System + First + Truncation + Last AI + Final user
    assert "truncated" in str(result[2].content).lower()
    assert result[3].content == "Last AI message"
    assert result[4].content == "Final user message"


@pytest.mark.ai
@patch("unique_deep_research.unique_custom.utils.prepare_messages_for_model")
@patch("unique_deep_research.unique_custom.utils.is_token_error")
async def test_ainvoke_with_token_handling__returns_result__on_success(
    mock_is_token_error, mock_prepare_messages
) -> None:
    """
    Purpose: Verify ainvoke_with_token_handling returns result on successful invocation.
    Why this matters: Ensures proper model invocation with token handling.
    Setup summary: Mock successful model invocation and verify result.
    """
    # Arrange
    mock_model = AsyncMock()
    mock_model.ainvoke.return_value = "Success"
    mock_prepare_messages.return_value = [HumanMessage(content="test")]
    model_info = Mock(spec=LanguageModelInfo)
    messages = cast(List[Any], [HumanMessage(content="test")])

    # Act
    result = await ainvoke_with_token_handling(mock_model, messages, model_info)

    # Assert
    assert result == "Success"
    mock_model.ainvoke.assert_called_once()


@pytest.mark.ai
@patch("unique_deep_research.unique_custom.utils.prepare_messages_for_model")
@patch("unique_deep_research.unique_custom.utils.is_token_error")
@patch("unique_deep_research.unique_custom.utils.remove_up_to_last_ai_message")
async def test_ainvoke_with_token_handling__retries_with_truncation__on_token_error(
    mock_remove_up_to_last_ai_message, mock_is_token_error, mock_prepare_messages
) -> None:
    """
    Purpose: Verify ainvoke_with_token_handling retries with truncation on token errors.
    Why this matters: Ensures graceful handling of token limit errors.
    Setup summary: Mock token error then success and verify retry with truncation.
    """
    # Arrange
    mock_model = AsyncMock()
    mock_model.ainvoke.side_effect = [Exception("token limit"), "Success"]
    mock_is_token_error.return_value = True
    mock_prepare_messages.return_value = [HumanMessage(content="test")]
    mock_remove_up_to_last_ai_message.return_value = [HumanMessage(content="truncated")]
    model_info = Mock(spec=LanguageModelInfo)
    messages = cast(List[Any], [HumanMessage(content="test")])

    # Act
    result = await ainvoke_with_token_handling(mock_model, messages, model_info)

    # Assert
    assert result == "Success"
    assert mock_model.ainvoke.call_count == 2
    mock_remove_up_to_last_ai_message.assert_called_once()


@pytest.mark.ai
@patch("unique_deep_research.unique_custom.utils.prepare_messages_for_model")
@patch("unique_deep_research.unique_custom.utils.is_token_error")
@patch("asyncio.sleep")
async def test_ainvoke_with_token_handling__retries_with_backoff__on_other_errors(
    mock_sleep, mock_is_token_error, mock_prepare_messages
) -> None:
    """
    Purpose: Verify ainvoke_with_token_handling retries with exponential backoff on other errors.
    Why this matters: Ensures resilient model invocation with proper retry logic.
    Setup summary: Mock non-token error then success and verify retry with backoff.
    """
    # Arrange
    mock_model = AsyncMock()
    mock_model.ainvoke.side_effect = [Exception("network error"), "Success"]
    mock_is_token_error.return_value = False
    mock_prepare_messages.return_value = [HumanMessage(content="test")]
    model_info = Mock(spec=LanguageModelInfo)
    messages = cast(List[Any], [HumanMessage(content="test")])

    # Act
    result = await ainvoke_with_token_handling(mock_model, messages, model_info)

    # Assert
    assert result == "Success"
    assert mock_model.ainvoke.call_count == 2
    mock_sleep.assert_called_once_with(5.0)  # Base delay


@pytest.mark.ai
@patch("unique_deep_research.unique_custom.utils.prepare_messages_for_model")
@patch("unique_deep_research.unique_custom.utils.is_token_error")
@patch("asyncio.sleep")
async def test_ainvoke_with_token_handling__raises_error__after_max_retries(
    mock_sleep, mock_is_token_error, mock_prepare_messages
) -> None:
    """
    Purpose: Verify ainvoke_with_token_handling raises error after max retries.
    Why this matters: Ensures proper error propagation after exhausting retry attempts.
    Setup summary: Mock persistent errors and verify final error is raised.
    """
    # Arrange
    mock_model = AsyncMock()
    mock_model.ainvoke.side_effect = Exception("persistent error")
    mock_is_token_error.return_value = False
    mock_prepare_messages.return_value = [HumanMessage(content="test")]
    model_info = Mock(spec=LanguageModelInfo)
    messages = cast(List[Any], [HumanMessage(content="test")])

    # Act & Assert
    with pytest.raises(Exception, match="persistent error"):
        await ainvoke_with_token_handling(mock_model, messages, model_info)

    assert mock_model.ainvoke.call_count == 5  # Initial + 4 retries
    assert mock_sleep.call_count == 4  # 4 retry delays
