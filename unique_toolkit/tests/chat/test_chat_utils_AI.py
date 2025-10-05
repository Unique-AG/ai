"""
AI-authored tests for chat utils module following comprehensive testing guidelines.

This module provides focused, well-documented tests for the chat utils functionality,
ensuring proper behavior of utility functions with clear test purposes and setup.
"""

import pytest

from unique_toolkit.chat.utils import convert_chat_history_to_injectable_string


@pytest.mark.ai
def test_convert_chat_history_to_injectable_string__formats_assistant_messages__with_proper_prefix_AI(
    base_chat_message,
):
    """
    Purpose: Ensure assistant messages are formatted with 'previous_answer:' prefix.
    Why this matters: Correct formatting is crucial for model context injection and conversation flow.
    Setup summary: Use base chat message fixture and verify proper formatting.
    """
    # Arrange
    history = [base_chat_message]

    # Act
    chat_history, token_length = convert_chat_history_to_injectable_string(history)

    # Assert
    assert len(chat_history) == 1
    assert chat_history[0] == f"previous_answer: {base_chat_message.content}"
    assert token_length > 0


@pytest.mark.ai
def test_convert_chat_history_to_injectable_string__formats_user_messages__with_proper_prefix_AI(
    base_user_message,
):
    """
    Purpose: Ensure user messages are formatted with 'previous_question:' prefix.
    Why this matters: Correct formatting distinguishes user input from assistant responses in model context.
    Setup summary: Use base user message fixture and verify proper formatting.
    """
    # Arrange
    history = [base_user_message]

    # Act
    chat_history, token_length = convert_chat_history_to_injectable_string(history)

    # Assert
    assert len(chat_history) == 1
    assert chat_history[0] == f"previous_question: {base_user_message.content}"
    assert token_length > 0


@pytest.mark.ai
def test_convert_chat_history_to_injectable_string__handles_mixed_conversation__with_correct_prefixes_AI(
    sample_messages_list,
):
    """
    Purpose: Ensure mixed conversation history maintains proper role-based formatting.
    Why this matters: Real conversations alternate between user and assistant, requiring correct prefix assignment.
    Setup summary: Use sample messages list fixture and verify each gets correct prefix.
    """
    # Arrange
    history = sample_messages_list

    # Act
    chat_history, token_length = convert_chat_history_to_injectable_string(history)

    # Assert
    assert len(chat_history) == 3
    assert chat_history[0] == f"previous_question: {sample_messages_list[0].content}"
    assert chat_history[1] == f"previous_answer: {sample_messages_list[1].content}"
    assert chat_history[2] == f"previous_question: {sample_messages_list[2].content}"
    assert token_length > 0


@pytest.mark.ai
def test_convert_chat_history_to_injectable_string__handles_empty_history__returns_empty_list_AI():
    """
    Purpose: Ensure empty chat history returns empty list and zero token count.
    Why this matters: Edge case handling prevents errors when no conversation history exists.
    Setup summary: Provide empty history list and verify empty result with zero tokens.
    """
    # Arrange
    history = []

    # Act
    chat_history, token_length = convert_chat_history_to_injectable_string(history)

    # Assert
    assert chat_history == []
    assert token_length == 0


@pytest.mark.ai
def test_convert_chat_history_to_injectable_string__calculates_token_length__for_context_injection_AI(
    base_user_message,
):
    """
    Purpose: Ensure token length calculation works correctly for context management.
    Why this matters: Token limits are critical for model input constraints and context window management.
    Setup summary: Use base user message fixture and verify token count is reasonable.
    """
    # Arrange
    history = [base_user_message]

    # Act
    chat_history, token_length = convert_chat_history_to_injectable_string(history)

    # Assert
    assert len(chat_history) == 1
    assert token_length > 0
    # Token count should be reasonable for the content length
    assert token_length >= 5  # Minimum expected tokens for the content
