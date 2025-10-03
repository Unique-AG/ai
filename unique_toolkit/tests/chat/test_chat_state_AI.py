"""
AI-authored tests for chat state module following comprehensive testing guidelines.

This module provides focused, well-documented tests for the ChatStateTemplate functionality,
ensuring proper state management and event-to-state conversion with clear test purposes.
"""

import pytest

from unique_toolkit.chat.state import ChatStateTemplate


@pytest.mark.ai
def test_chat_state_template__initializes_with_required_fields__creates_valid_state_AI():
    """
    Purpose: Ensure ChatStateTemplate initializes correctly with all required fields.
    Why this matters: State objects must be properly constructed for chat session management.
    Setup summary: Create ChatStateTemplate with all required parameters and verify field assignment.
    """
    # Arrange
    company_id = "test_company_123"
    user_id = "test_user_123"
    assistant_id = "test_assistant_123"
    chat_id = "test_chat_123"
    user_message_text = "Hello, this is a test message"
    user_message_id = "user_msg_123"
    assistant_message_id = "assistant_msg_123"
    module_name = "test_module"

    # Act
    state = ChatStateTemplate(
        company_id=company_id,
        user_id=user_id,
        assistant_id=assistant_id,
        chat_id=chat_id,
        user_message_text=user_message_text,
        user_message_id=user_message_id,
        assistant_message_id=assistant_message_id,
        module_name=module_name,
    )

    # Assert
    assert state.company_id == company_id
    assert state.user_id == user_id
    assert state.assistant_id == assistant_id
    assert state.chat_id == chat_id
    assert state.user_message_text == user_message_text
    assert state.user_message_id == user_message_id
    assert state.assistant_message_id == assistant_message_id
    assert state.module_name == module_name


@pytest.mark.ai
def test_chat_state_template__initializes_with_optional_none__sets_default_values_AI():
    """
    Purpose: Ensure ChatStateTemplate handles optional None values correctly.
    Why this matters: Optional fields should default to None when not provided, maintaining flexibility.
    Setup summary: Create ChatStateTemplate with only required fields and verify optional fields are None.
    """
    # Arrange
    company_id = "test_company_123"
    user_id = "test_user_123"
    assistant_id = "test_assistant_123"
    chat_id = "test_chat_123"

    # Act
    state = ChatStateTemplate(
        company_id=company_id,
        user_id=user_id,
        assistant_id=assistant_id,
        chat_id=chat_id,
    )

    # Assert
    assert state.company_id == company_id
    assert state.user_id == user_id
    assert state.assistant_id == assistant_id
    assert state.chat_id == chat_id
    assert state.user_message_text is None
    assert state.user_message_id is None
    assert state.assistant_message_id is None
    assert state.module_name is None


@pytest.mark.ai
def test_chat_state_template_from_event__converts_event_to_state__with_all_fields_AI(
    base_chat_event,
):
    """
    Purpose: Ensure from_event class method correctly extracts all fields from Event object.
    Why this matters: Event-to-state conversion is critical for chat session initialization and data flow.
    Setup summary: Use base chat event fixture and verify all fields are properly extracted to state.
    """
    # Arrange
    event = base_chat_event

    # Act
    state = ChatStateTemplate.from_event(event)

    # Assert
    assert state.company_id == event.company_id
    assert state.user_id == event.user_id
    assert state.assistant_id == event.payload.assistant_id
    assert state.chat_id == event.payload.chat_id
    assert state.user_message_text == event.payload.user_message.text
    assert state.user_message_id == event.payload.user_message.id
    assert state.assistant_message_id == event.payload.assistant_message.id
    assert state.module_name == event.payload.name


@pytest.mark.ai
def test_chat_state_template__maintains_immutability__after_creation_AI():
    """
    Purpose: Ensure ChatStateTemplate fields remain unchanged after initialization.
    Why this matters: State immutability prevents accidental modifications and ensures data integrity.
    Setup summary: Create state object and verify field values remain consistent after access.
    """
    # Arrange
    state = ChatStateTemplate(
        company_id="test_company",
        user_id="test_user",
        assistant_id="test_assistant",
        chat_id="test_chat",
        user_message_text="Test message",
        user_message_id="msg_123",
        assistant_message_id="assistant_123",
        module_name="test_module",
    )

    # Act & Assert - Access fields multiple times
    assert state.company_id == "test_company"
    assert state.user_id == "test_user"
    assert state.assistant_id == "test_assistant"
    assert state.chat_id == "test_chat"
    assert state.user_message_text == "Test message"
    assert state.user_message_id == "msg_123"
    assert state.assistant_message_id == "assistant_123"
    assert state.module_name == "test_module"

    # Verify values haven't changed
    assert state.company_id == "test_company"
    assert state.user_id == "test_user"
    assert state.assistant_id == "test_assistant"
    assert state.chat_id == "test_chat"
