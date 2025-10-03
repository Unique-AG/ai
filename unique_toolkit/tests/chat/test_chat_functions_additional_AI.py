"""
AI-authored tests for additional chat functions following comprehensive testing guidelines.

This module provides focused, well-documented tests for missing function coverage in chat functions,
ensuring proper behavior of utility functions, message processing, and SDK integration with clear test purposes.
"""

from unittest.mock import patch

import pytest
import unique_sdk

from unique_toolkit.chat.functions import (
    _construct_message_create_params,
    _construct_message_modify_params,
    create_message_assessment,
    create_message_execution,
    create_message_log,
    get_message_execution,
    list_messages,
    map_references,
    map_references_with_original_index,
    map_to_chat_messages,
    modify_message_assessment,
    update_message_execution,
    update_message_log,
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


@pytest.mark.ai
def test_map_references__converts_content_references__to_sdk_format_AI(
    base_content_reference,
):
    """
    Purpose: Ensure map_references converts ContentReference objects to SDK-compatible dictionary format.
    Why this matters: SDK integration requires specific field names and structure for reference data.
    Setup summary: Use base content reference fixture and verify proper conversion to SDK format.
    """
    # Arrange
    references = [base_content_reference]

    # Act
    result = map_references(references)

    # Assert
    assert len(result) == 1
    assert result[0]["name"] == base_content_reference.name
    assert result[0]["url"] == base_content_reference.url
    assert result[0]["sequenceNumber"] == base_content_reference.sequence_number
    assert result[0]["sourceId"] == base_content_reference.source_id
    assert result[0]["source"] == base_content_reference.source


@pytest.mark.ai
def test_map_references__handles_empty_list__returns_empty_list_AI():
    """
    Purpose: Ensure map_references handles empty reference lists gracefully.
    Why this matters: Edge case handling prevents errors when no references are provided.
    Setup summary: Provide empty reference list and verify empty result.
    """
    # Arrange
    references = []

    # Act
    result = map_references(references)

    # Assert
    assert result == []


@pytest.mark.ai
def test_map_references_with_original_index__preserves_index_mapping__for_tracking_AI(
    sample_references_list,
):
    """
    Purpose: Ensure map_references_with_original_index maintains mapping between original and converted references.
    Why this matters: Index tracking is crucial for maintaining reference order and debugging.
    Setup summary: Use sample references list fixture and verify index mapping is preserved in conversion.
    """
    # Arrange
    references = sample_references_list

    # Act
    result = map_references_with_original_index(references)

    # Assert
    assert len(result) == 2
    # Verify index mapping is preserved
    assert result[0]["originalIndex"] == references[0].original_index
    assert result[1]["originalIndex"] == references[1].original_index
    assert result[0]["name"] == references[0].name
    assert result[1]["name"] == references[1].name


@pytest.mark.ai
def test_construct_message_modify_params__builds_correct_parameters__for_sdk_call_AI(
    base_content_reference,
):
    """
    Purpose: Ensure _construct_message_modify_params builds proper parameter dictionary for SDK calls.
    Why this matters: Correct parameter construction is essential for successful SDK integration and message modification.
    Setup summary: Use base content reference fixture and verify proper SDK parameter dictionary construction.
    """
    # Arrange
    user_id = "test_user"
    company_id = "test_company"
    assistant_message_id = "assistant_123"
    chat_id = "chat_123"
    user_message_id = "user_123"
    user_message_text = "Test message"
    assistant = True
    content = "Modified content"
    original_content = "Original content"
    references = [base_content_reference]
    debug_info = {"test": "debug"}
    message_id = "msg_123"
    set_completed_at = True

    # Act
    result = _construct_message_modify_params(
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

    # Assert
    assert result["user_id"] == user_id
    assert result["company_id"] == company_id
    assert result["id"] == message_id
    assert result["chatId"] == chat_id
    assert result["text"] == content
    assert result["originalText"] == original_content
    assert "references" in result
    assert result["debugInfo"] == debug_info
    assert "completedAt" in result


@pytest.mark.ai
def test_construct_message_create_params__builds_correct_parameters__for_message_creation_AI(
    base_content_reference,
):
    """
    Purpose: Ensure _construct_message_create_params builds proper parameter dictionary for message creation.
    Why this matters: Correct parameter construction is essential for successful message creation via SDK.
    Setup summary: Use base content reference fixture and verify proper SDK parameter dictionary construction.
    """
    # Arrange
    user_id = "test_user"
    company_id = "test_company"
    chat_id = "chat_123"
    assistant_id = "assistant_123"
    role = ChatMessageRole.ASSISTANT
    content = "New message content"
    original_content = "New message content"
    references = [base_content_reference]
    debug_info = {"test": "debug"}
    set_completed_at = True

    # Act
    result = _construct_message_create_params(
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

    # Assert
    assert result["user_id"] == user_id
    assert result["company_id"] == company_id
    assert result["chatId"] == chat_id
    assert result["assistantId"] == assistant_id
    assert result["role"] == role.value.upper()
    assert result["text"] == content
    assert result["originalText"] == original_content
    assert "references" in result
    assert result["debugInfo"] == debug_info
    assert "completedAt" in result


@pytest.mark.ai
def test_map_to_chat_messages__converts_sdk_data__to_chat_message_objects_AI(
    sample_sdk_messages_list,
):
    """
    Purpose: Ensure map_to_chat_messages converts SDK message data to ChatMessage objects.
    Why this matters: Proper object conversion is essential for type safety and consistent message handling.
    Setup summary: Use sample SDK messages list fixture and verify proper ChatMessage object creation.
    """
    # Arrange
    messages_data = sample_sdk_messages_list["data"]

    # Act
    result = map_to_chat_messages(messages_data)

    # Assert
    assert len(result) == 2
    assert all(isinstance(msg, ChatMessage) for msg in result)
    assert result[0].id == messages_data[0]["id"]
    assert result[0].role.value.upper() == messages_data[0]["role"]
    assert result[0].content == messages_data[0]["text"]
    assert result[1].id == messages_data[1]["id"]
    assert result[1].role.value.upper() == messages_data[1]["role"]
    assert result[1].content == messages_data[1]["text"]


@pytest.mark.ai
@patch.object(unique_sdk.Message, "list")
def test_list_messages__calls_sdk_correctly__returns_message_list_AI(mock_list):
    """
    Purpose: Ensure list_messages calls SDK with correct parameters and returns message list.
    Why this matters: Proper SDK integration is essential for retrieving chat history and message data.
    Setup summary: Mock SDK list method and verify correct parameters and return value handling.
    """
    # Arrange
    mock_list.return_value = {
        "object": "list",
        "data": [
            {
                "id": "msg_1",
                "chatId": "chat_123",
                "text": "Test message",
                "role": "USER",
                "originalText": "Test message",
                "createdAt": "2024-01-01T12:00:00Z",
                "updatedAt": "2024-01-01T12:00:00Z",
                "completedAt": None,
                "debugInfo": None,
                "references": [],
            }
        ],
    }

    # Act
    result = list_messages("test_user", "test_company", "test_chat")

    # Assert
    mock_list.assert_called_once_with(
        user_id="test_user",
        company_id="test_company",
        chatId="test_chat",
    )
    assert result == mock_list.return_value


@pytest.mark.ai
@patch.object(unique_sdk.MessageAssessment, "create")
def test_create_message_assessment__creates_assessment__with_correct_parameters_AI(
    mock_create,
):
    """
    Purpose: Ensure create_message_assessment calls SDK with correct parameters for assessment creation.
    Why this matters: Message assessments are crucial for quality control and content evaluation.
    Setup summary: Mock SDK create method and verify correct parameters and return value handling.
    """
    # Arrange
    mock_create.return_value = {
        "id": "assessment_123",
        "messageId": "msg_123",
        "status": "DONE",
        "explanation": "Test assessment",
        "label": "GREEN",
        "type": "HALLUCINATION",
        "isVisible": True,
        "title": None,
        "createdAt": "2024-01-01T12:00:00Z",
        "updatedAt": "2024-01-01T12:00:00Z",
        "object": "message_assessment",
    }

    # Act
    result = create_message_assessment(
        user_id="test_user",
        company_id="test_company",
        assistant_message_id="msg_123",
        status=ChatMessageAssessmentStatus.DONE,
        explanation="Test assessment",
        label=ChatMessageAssessmentLabel.GREEN,
        type=ChatMessageAssessmentType.HALLUCINATION,
        is_visible=True,
    )

    # Assert
    mock_create.assert_called_once_with(
        user_id="test_user",
        company_id="test_company",
        messageId="msg_123",
        status="DONE",
        explanation="Test assessment",
        label="GREEN",
        type="HALLUCINATION",
        isVisible=True,
        title=None,
    )
    assert isinstance(result, ChatMessageAssessment)


@pytest.mark.ai
@patch.object(unique_sdk.MessageAssessment, "modify")
def test_modify_message_assessment__modifies_assessment__with_correct_parameters_AI(
    mock_modify,
):
    """
    Purpose: Ensure modify_message_assessment calls SDK with correct parameters for assessment modification.
    Why this matters: Assessment modification is essential for updating evaluation results and feedback.
    Setup summary: Mock SDK modify method and verify correct parameters and return value handling.
    """
    # Arrange
    mock_modify.return_value = {
        "id": "assessment_123",
        "messageId": "msg_123",
        "status": "DONE",
        "explanation": "Updated assessment",
        "label": "RED",
        "type": "HALLUCINATION",
        "isVisible": True,
        "title": "Updated Title",
        "createdAt": "2024-01-01T12:00:00Z",
        "updatedAt": "2024-01-01T12:00:00Z",
        "object": "message_assessment",
    }

    # Act
    result = modify_message_assessment(
        user_id="test_user",
        company_id="test_company",
        assistant_message_id="msg_123",
        status=ChatMessageAssessmentStatus.DONE,
        explanation="Updated assessment",
        label=ChatMessageAssessmentLabel.RED,
        type=ChatMessageAssessmentType.HALLUCINATION,
        title="Updated Title",
    )

    # Assert
    mock_modify.assert_called_once_with(
        user_id="test_user",
        company_id="test_company",
        messageId="msg_123",
        status="DONE",
        explanation="Updated assessment",
        label="RED",
        type="HALLUCINATION",
        title="Updated Title",
    )
    assert isinstance(result, ChatMessageAssessment)


@pytest.mark.ai
@patch.object(unique_sdk.MessageLog, "create")
def test_create_message_log__creates_log__with_correct_parameters_AI(mock_create):
    """
    Purpose: Ensure create_message_log calls SDK with correct parameters for log creation.
    Why this matters: Message logs are essential for tracking processing details and debugging.
    Setup summary: Mock SDK create method and verify correct parameters and return value handling.
    """
    # Arrange
    mock_create.return_value = {
        "message_log_id": "log_123",
        "message_id": "msg_123",
        "status": "COMPLETED",
        "text": "Test log entry",
        "order": 1,
        "details": {
            "data": [],
            "status": "completed",
        },
        "uncitedReferences": {
            "data": [],
        },
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "object": "message_log",
    }

    # Act
    result = create_message_log(
        user_id="test_user",
        company_id="test_company",
        message_id="msg_123",
        text="Test log entry",
        status=MessageLogStatus.COMPLETED,
        order=1,
        details=MessageLogDetails(
            data=[],
            status="completed",
        ),
        uncited_references=MessageLogUncitedReferences(
            data=[],
        ),
    )

    # Assert
    mock_create.assert_called_once()
    assert isinstance(result, MessageLog)


@pytest.mark.ai
@patch.object(unique_sdk.MessageLog, "update")
def test_update_message_log__updates_log__with_correct_parameters_AI(mock_modify):
    """
    Purpose: Ensure update_message_log calls SDK with correct parameters for log updates.
    Why this matters: Log updates are essential for maintaining accurate processing information.
    Setup summary: Mock SDK modify method and verify correct parameters and return value handling.
    """
    # Arrange
    mock_modify.return_value = {
        "message_log_id": "log_123",
        "message_id": "msg_123",
        "status": "COMPLETED",
        "text": "Updated log entry",
        "order": 1,
        "details": {
            "data": [],
            "status": "updated",
        },
        "uncitedReferences": {
            "data": [],
        },
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:01:00Z",
        "object": "message_log",
    }

    # Act
    result = update_message_log(
        user_id="test_user",
        company_id="test_company",
        message_log_id="log_123",
        order=1,
        text="Updated log entry",
        status=MessageLogStatus.COMPLETED,
        details=MessageLogDetails(
            data=[],
            status="updated",
        ),
        uncited_references=MessageLogUncitedReferences(
            data=[],
        ),
    )

    # Assert
    mock_modify.assert_called_once()
    assert isinstance(result, MessageLog)


@pytest.mark.ai
@patch.object(unique_sdk.MessageExecution, "create")
def test_create_message_execution__creates_execution__with_correct_parameters_AI(
    mock_create,
):
    """
    Purpose: Ensure create_message_execution calls SDK with correct parameters for execution creation.
    Why this matters: Message executions track tool calls and function executions for debugging.
    Setup summary: Mock SDK create method and verify correct parameters and return value handling.
    """
    # Arrange
    mock_create.return_value = {
        "id": "execution_123",
        "message_id": "msg_123",
        "type": "DEEP_RESEARCH",
        "status": "COMPLETED",
        "seconds_remaining": 60,
        "percentage_completed": 50,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "object": "message_execution",
    }

    # Act
    result = create_message_execution(
        user_id="test_user",
        company_id="test_company",
        message_id="msg_123",
        chat_id="chat_123",
        type=MessageExecutionType.DEEP_RESEARCH,
        seconds_remaining=60,
        percentage_completed=50,
    )

    # Assert
    mock_create.assert_called_once()
    assert isinstance(result, MessageExecution)


@pytest.mark.ai
@patch.object(unique_sdk.MessageExecution, "get")
def test_get_message_execution__retrieves_execution__with_correct_parameters_AI(
    mock_list,
):
    """
    Purpose: Ensure get_message_execution calls SDK with correct parameters for execution retrieval.
    Why this matters: Execution retrieval is essential for debugging and monitoring tool calls.
    Setup summary: Mock SDK list method and verify correct parameters and return value handling.
    """
    # Arrange
    mock_list.return_value = {
        "id": "execution_123",
        "message_id": "msg_123",
        "type": "DEEP_RESEARCH",
        "status": "COMPLETED",
        "seconds_remaining": 30,
        "percentage_completed": 100,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "object": "message_execution",
    }

    # Act
    result = get_message_execution("test_user", "test_company", "msg_123")

    # Assert
    mock_list.assert_called_once_with(
        user_id="test_user",
        company_id="test_company",
        messageId="msg_123",
    )
    assert isinstance(result, MessageExecution)
    assert result.message_id == "msg_123"
    assert result.type == MessageExecutionType.DEEP_RESEARCH


@pytest.mark.ai
@patch.object(unique_sdk.MessageExecution, "update")
def test_update_message_execution__updates_execution__with_correct_parameters_AI(
    mock_modify,
):
    """
    Purpose: Ensure update_message_execution calls SDK with correct parameters for execution updates.
    Why this matters: Execution updates are essential for tracking tool call progress and results.
    Setup summary: Mock SDK modify method and verify correct parameters and return value handling.
    """
    # Arrange
    mock_modify.return_value = {
        "id": "execution_123",
        "message_id": "msg_123",
        "type": "DEEP_RESEARCH",
        "status": "COMPLETED",
        "seconds_remaining": 30,
        "percentage_completed": 100,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:01:00Z",
        "object": "message_execution",
    }

    # Act
    result = update_message_execution(
        user_id="test_user",
        company_id="test_company",
        message_id="msg_123",
        status=MessageExecutionUpdateStatus.COMPLETED,
        seconds_remaining=30,
        percentage_completed=100,
    )

    # Assert
    mock_modify.assert_called_once()
    assert isinstance(result, MessageExecution)
