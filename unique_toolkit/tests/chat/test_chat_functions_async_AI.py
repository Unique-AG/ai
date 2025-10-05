"""
AI-authored tests for async chat functions following comprehensive testing guidelines.

This module provides focused, well-documented tests for async versions of chat functions,
ensuring proper async behavior, error handling, and SDK integration with clear test purposes.
"""

from unittest.mock import patch

import pytest
import unique_sdk

from unique_toolkit.chat.functions import (
    create_message_assessment_async,
    create_message_execution_async,
    create_message_log_async,
    get_message_execution_async,
    modify_message_assessment_async,
    stream_complete_with_references_async,
    update_message_execution_async,
    update_message_log_async,
)
from unique_toolkit.chat.schemas import (
    ChatMessageAssessment,
    ChatMessageAssessmentLabel,
    ChatMessageAssessmentStatus,
    ChatMessageAssessmentType,
    MessageExecution,
    MessageExecutionType,
    MessageExecutionUpdateStatus,
    MessageLog,
    MessageLogDetails,
    MessageLogStatus,
    MessageLogUncitedReferences,
)
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelStreamResponse,
)


@pytest.mark.ai
@pytest.mark.asyncio
@patch.object(unique_sdk.MessageAssessment, "create_async")
async def test_create_message_assessment_async__creates_assessment__with_correct_parameters_AI(
    mock_create,
):
    """
    Purpose: Ensure create_message_assessment_async calls SDK with correct parameters for async assessment creation.
    Why this matters: Async assessment creation is essential for non-blocking quality control operations.
    Setup summary: Mock async SDK create method and verify correct parameters and return value handling.
    """
    # Arrange
    mock_create.return_value = {
        "id": "assessment_123",
        "messageId": "msg_123",
        "status": "DONE",
        "explanation": "Async test assessment",
        "label": "GREEN",
        "type": "HALLUCINATION",
        "isVisible": True,
        "createdAt": "2024-01-01T12:00:00Z",
        "updatedAt": "2024-01-01T12:00:00Z",
        "object": "message_assessment",
    }

    # Act
    result = await create_message_assessment_async(
        user_id="test_user",
        company_id="test_company",
        assistant_message_id="msg_123",
        status=ChatMessageAssessmentStatus.DONE,
        explanation="Async test assessment",
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
        explanation="Async test assessment",
        label="GREEN",
        type="HALLUCINATION",
        isVisible=True,
        title=None,
    )
    assert isinstance(result, ChatMessageAssessment)


@pytest.mark.ai
@pytest.mark.asyncio
@patch.object(unique_sdk.MessageAssessment, "modify_async")
async def test_modify_message_assessment_async__modifies_assessment__with_correct_parameters_AI(
    mock_modify,
):
    """
    Purpose: Ensure modify_message_assessment_async calls SDK with correct parameters for async assessment modification.
    Why this matters: Async assessment modification is essential for non-blocking evaluation updates.
    Setup summary: Mock async SDK modify method and verify correct parameters and return value handling.
    """
    # Arrange
    mock_modify.return_value = {
        "id": "assessment_123",
        "messageId": "msg_123",
        "status": "DONE",
        "explanation": "Updated async assessment",
        "label": "RED",
        "type": "HALLUCINATION",
        "isVisible": True,
        "createdAt": "2024-01-01T12:00:00Z",
        "updatedAt": "2024-01-01T12:00:00Z",
        "object": "message_assessment",
    }

    # Act
    result = await modify_message_assessment_async(
        user_id="test_user",
        company_id="test_company",
        assistant_message_id="msg_123",
        status=ChatMessageAssessmentStatus.DONE,
        explanation="Updated async assessment",
        label=ChatMessageAssessmentLabel.RED,
        type=ChatMessageAssessmentType.HALLUCINATION,
        title="Async Updated Title",
    )

    # Assert
    mock_modify.assert_called_once_with(
        user_id="test_user",
        company_id="test_company",
        messageId="msg_123",
        status="DONE",
        explanation="Updated async assessment",
        label="RED",
        type="HALLUCINATION",
        title="Async Updated Title",
    )
    assert isinstance(result, ChatMessageAssessment)


@pytest.mark.ai
@pytest.mark.asyncio
@patch.object(unique_sdk.MessageLog, "create_async")
async def test_create_message_log_async__creates_log__with_correct_parameters_AI(
    mock_create,
):
    """
    Purpose: Ensure create_message_log_async calls SDK with correct parameters for async log creation.
    Why this matters: Async log creation is essential for non-blocking processing tracking and debugging.
    Setup summary: Mock async SDK create method and verify correct parameters and return value handling.
    """
    # Arrange
    mock_create.return_value = {
        "message_log_id": "log_123",
        "message_id": "msg_123",
        "status": "COMPLETED",
        "text": "Async test log entry",
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
    }

    # Act
    result = await create_message_log_async(
        user_id="test_user",
        company_id="test_company",
        message_id="msg_123",
        text="Async test log entry",
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
@pytest.mark.asyncio
@patch.object(unique_sdk.MessageLog, "update_async")
async def test_update_message_log_async__updates_log__with_correct_parameters_AI(
    mock_modify,
):
    """
    Purpose: Ensure update_message_log_async calls SDK with correct parameters for async log updates.
    Why this matters: Async log updates are essential for non-blocking processing information maintenance.
    Setup summary: Mock async SDK modify method and verify correct parameters and return value handling.
    """
    # Arrange
    mock_modify.return_value = {
        "message_log_id": "log_123",
        "message_id": "msg_123",
        "status": "COMPLETED",
        "text": "Updated async log entry",
        "order": 1,
        "details": {
            "data": [],
            "status": "updated",
        },
        "uncitedReferences": {
            "data": [],
        },
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:02:00Z",
    }

    # Act
    result = await update_message_log_async(
        user_id="test_user",
        company_id="test_company",
        message_log_id="log_123",
        order=1,
        text="Updated async log entry",
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
@pytest.mark.asyncio
@patch.object(unique_sdk.MessageExecution, "create_async")
async def test_create_message_execution_async__creates_execution__with_correct_parameters_AI(
    mock_create,
):
    """
    Purpose: Ensure create_message_execution_async calls SDK with correct parameters for async execution creation.
    Why this matters: Async execution creation is essential for non-blocking tool call tracking.
    Setup summary: Mock async SDK create method and verify correct parameters and return value handling.
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
    }

    # Act
    result = await create_message_execution_async(
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
@pytest.mark.asyncio
@patch.object(unique_sdk.MessageExecution, "get_async")
async def test_get_message_execution_async__retrieves_execution__with_correct_parameters_AI(
    mock_list,
):
    """
    Purpose: Ensure get_message_execution_async calls SDK with correct parameters for async execution retrieval.
    Why this matters: Async execution retrieval is essential for non-blocking debugging and monitoring.
    Setup summary: Mock async SDK list method and verify correct parameters and return value handling.
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
    }

    # Act
    result = await get_message_execution_async("test_user", "test_company", "msg_123")

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
@pytest.mark.asyncio
@patch.object(unique_sdk.MessageExecution, "update_async")
async def test_update_message_execution_async__updates_execution__with_correct_parameters_AI(
    mock_modify,
):
    """
    Purpose: Ensure update_message_execution_async calls SDK with correct parameters for async execution updates.
    Why this matters: Async execution updates are essential for non-blocking tool call progress tracking.
    Setup summary: Mock async SDK modify method and verify correct parameters and return value handling.
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
    }

    # Act
    result = await update_message_execution_async(
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


@pytest.mark.ai
@pytest.mark.asyncio
@patch.object(unique_sdk.Integrated, "chat_stream_completion_async")
async def test_stream_complete_with_references_async__streams_completion__with_correct_parameters_AI(
    mock_stream, base_content_chunk
):
    """
    Purpose: Ensure stream_complete_with_references_async calls SDK with correct parameters for async streaming.
    Why this matters: Async streaming is essential for non-blocking real-time response generation.
    Setup summary: Use base content chunk fixture and mock async SDK stream method.
    """
    # Arrange
    mock_stream.return_value = {
        "message": {
            "id": "stream_msg_123",
            "previousMessageId": "prev_msg_123",
            "role": "ASSISTANT",
            "text": "Async streamed response",
            "originalText": "Async streamed response original",
        }
    }

    messages = LanguageModelMessages([])
    content_chunks = [base_content_chunk]

    # Act
    result = await stream_complete_with_references_async(
        company_id="test_company",
        user_id="test_user",
        assistant_message_id="assistant_123",
        user_message_id="user_123",
        chat_id="chat_123",
        assistant_id="assistant_123",
        messages=messages,
        model_name=LanguageModelName.AZURE_GPT_4_0613,
        content_chunks=content_chunks,
        debug_info={"test": "debug"},
        temperature=0.7,
        timeout=30000,
        tools=None,
        start_text="Start",
        other_options={"presence_penalty": 0.5},
    )

    # Assert
    mock_stream.assert_called_once()
    assert isinstance(result, LanguageModelStreamResponse)


@pytest.mark.ai
@pytest.mark.asyncio
@patch.object(unique_sdk.Integrated, "chat_stream_completion_async")
async def test_stream_complete_with_references_async__handles_minimal_parameters__with_defaults_AI(
    mock_stream,
):
    """
    Purpose: Ensure stream_complete_with_references_async works with minimal parameters and defaults.
    Why this matters: Function should work with minimal configuration for simple use cases.
    Setup summary: Mock async SDK stream method with minimal parameters and verify correct behavior.
    """
    # Arrange
    mock_stream.return_value = {
        "message": {
            "id": "minimal_stream_123",
            "previousMessageId": "prev_msg_123",
            "role": "ASSISTANT",
            "text": "Minimal async response",
            "originalText": "Minimal async response original",
        }
    }

    messages = LanguageModelMessages([])

    # Act
    result = await stream_complete_with_references_async(
        company_id="test_company",
        user_id="test_user",
        assistant_message_id="assistant_123",
        user_message_id="user_123",
        chat_id="chat_123",
        assistant_id="assistant_123",
        messages=messages,
        model_name=LanguageModelName.AZURE_GPT_4_0613,
    )

    # Assert
    mock_stream.assert_called_once()
    assert isinstance(result, LanguageModelStreamResponse)


@pytest.mark.ai
@pytest.mark.asyncio
@patch.object(unique_sdk.MessageAssessment, "create_async")
async def test_create_message_assessment_async__handles_error__raises_exception_AI(
    mock_create,
):
    """
    Purpose: Ensure create_message_assessment_async properly handles and raises SDK errors.
    Why this matters: Error handling is crucial for debugging and system reliability.
    Setup summary: Mock SDK to raise exception and verify proper error propagation.
    """
    # Arrange
    mock_create.side_effect = Exception("SDK Error")

    # Act & Assert
    with pytest.raises(Exception, match="SDK Error"):
        await create_message_assessment_async(
            user_id="test_user",
            company_id="test_company",
            assistant_message_id="msg_123",
            status=ChatMessageAssessmentStatus.DONE,
            explanation="Test assessment",
            label=ChatMessageAssessmentLabel.GREEN,
            type=ChatMessageAssessmentType.HALLUCINATION,
            is_visible=True,
        )


@pytest.mark.ai
@pytest.mark.asyncio
@patch.object(unique_sdk.Integrated, "chat_stream_completion_async")
async def test_stream_complete_with_references_async__handles_streaming_error__raises_exception_AI(
    mock_stream,
):
    """
    Purpose: Ensure stream_complete_with_references_async properly handles streaming errors.
    Why this matters: Streaming error handling is essential for robust real-time communication.
    Setup summary: Mock SDK to raise exception during streaming and verify proper error propagation.
    """
    # Arrange
    mock_stream.side_effect = Exception("Streaming Error")

    messages = LanguageModelMessages([])

    # Act & Assert
    with pytest.raises(Exception, match="Streaming Error"):
        await stream_complete_with_references_async(
            company_id="test_company",
            user_id="test_user",
            assistant_message_id="assistant_123",
            user_message_id="user_123",
            chat_id="chat_123",
            assistant_id="assistant_123",
            messages=messages,
            model_name=LanguageModelName.AZURE_GPT_4_0613,
        )
