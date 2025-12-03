"""
Unit tests for service.py module.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.chat.schemas import MessageExecutionUpdateStatus

from unique_deep_research.config import DeepResearchToolConfig
from unique_deep_research.service import (
    DeepResearchTool,
    DeepResearchToolInput,
    MemorySchema,
)


class MockRole:
    """Mock role class that behaves like an enum."""

    def __init__(self, value: str):
        self.value = value

    def __eq__(self, other):
        return self.value == other


@pytest.mark.ai
def test_deep_research_tool__is_message_execution__returns_false__when_no_execution_id() -> (
    None
):
    """
    Purpose: Verify DeepResearchTool.is_message_execution() returns False when no execution_id.
    Why this matters: Determines if tool is running in message execution mode.
    Setup summary: Create tool with no execution_id and verify False is returned.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                # Act
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                result = tool.is_message_execution()

                # Assert
                assert result is False


@pytest.mark.ai
def test_deep_research_tool__is_message_execution__returns_true__when_execution_id_present() -> (
    None
):
    """
    Purpose: Verify DeepResearchTool.is_message_execution() returns True when execution_id present.
    Why this matters: Determines if tool is running in message execution mode.
    Setup summary: Create tool with execution_id and verify True is returned.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = "test-execution-id"
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                # Act
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                result = tool.is_message_execution()

                # Assert
                assert result is True


@pytest.mark.ai
def test_deep_research_tool__get_user_request__returns_user_message_text() -> None:
    """
    Purpose: Verify DeepResearchTool.get_user_request() returns user message text.
    Why this matters: Provides access to user's research request.
    Setup summary: Create tool with user message and verify text is returned.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Research AI trends"
    mock_event.payload.user_message.original_text = "Research AI trends"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                # Act
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                result = tool.get_user_request()

                # Assert
                assert result == "Research AI trends"


@pytest.mark.ai
def test_deep_research_tool__get_user_request__returns_original_text__when_text_is_none() -> (
    None
):
    """
    Purpose: Verify DeepResearchTool.get_user_request() returns original_text when text is None.
    Why this matters: Ensures fallback to original_text when text field is empty.
    Setup summary: Create tool with None text but original_text and verify fallback.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = None
    mock_event.payload.user_message.original_text = "Original research request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                # Act
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                result = tool.get_user_request()

                # Assert
                assert result == "Original research request"


@pytest.mark.ai
def test_deep_research_tool__get_user_request__returns_empty_string__when_both_text_fields_none() -> (
    None
):
    """
    Purpose: Verify DeepResearchTool.get_user_request() returns empty string when both text fields are None.
    Why this matters: Ensures graceful handling when no user text is available.
    Setup summary: Create tool with both text fields None and verify empty string is returned.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = None
    mock_event.payload.user_message.original_text = None
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                # Act
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                result = tool.get_user_request()

                # Assert
                assert result == ""


@pytest.mark.ai
def test_deep_research_tool__tool_description__returns_correct_description() -> None:
    """
    Purpose: Verify DeepResearchTool.tool_description() returns correct description.
    Why this matters: Tool description is used for LLM tool selection.
    Setup summary: Create tool and verify tool description is correct.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                # Act
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                description = tool.tool_description()

                # Assert
                assert description.name == "DeepResearch"
                assert "complex research tasks" in description.description
                assert description.parameters == DeepResearchToolInput


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__get_followup_question_message_id__returns_none__when_no_memory() -> (
    None
):
    """
    Purpose: Verify get_followup_question_message_id returns None when no memory is loaded.
    Why this matters: Ensures proper handling when no follow-up question was previously asked.
    Setup summary: Mock memory service to return None, verify None is returned.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                tool.memory_service.load_async = AsyncMock(return_value=None)

                # Act
                result = await tool.get_followup_question_message_id()

                # Assert
                assert result is None


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__get_followup_question_message_id__returns_message_id__when_memory_exists() -> (
    None
):
    """
    Purpose: Verify get_followup_question_message_id returns message_id when memory exists.
    Why this matters: Retrieves stored follow-up question message ID for conversation flow.
    Setup summary: Mock memory service to return MemorySchema with message_id, verify ID is returned.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                mock_memory = MemorySchema(message_id="followup-msg-123")
                tool.memory_service.load_async = AsyncMock(return_value=mock_memory)

                # Act
                result = await tool.get_followup_question_message_id()

                # Assert
                assert result == "followup-msg-123"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__is_followup_question_answer__returns_false__when_no_followup_message_id() -> (
    None
):
    """
    Purpose: Verify is_followup_question_answer returns False when no follow-up message ID exists.
    Why this matters: Determines if current message is answering a follow-up question.
    Setup summary: Mock get_followup_question_message_id to return None, verify False is returned.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                tool.get_followup_question_message_id = AsyncMock(return_value=None)

                # Act
                result = await tool.is_followup_question_answer()

                # Assert
                assert result is False


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__is_followup_question_answer__returns_false__when_history_empty() -> (
    None
):
    """
    Purpose: Verify is_followup_question_answer returns False when chat history is empty.
    Why this matters: Ensures proper handling when no chat history is available.
    Setup summary: Mock get_followup_question_message_id and get_full_history_async, verify False is returned.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                tool.get_followup_question_message_id = AsyncMock(
                    return_value="followup-msg-123"
                )
                tool.chat_service.get_full_history_async = AsyncMock(return_value=None)

                # Act
                result = await tool.is_followup_question_answer()

                # Assert
                assert result is False


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__is_followup_question_answer__returns_true__when_last_message_matches() -> (
    None
):
    """
    Purpose: Verify is_followup_question_answer returns True when last message matches follow-up ID.
    Why this matters: Correctly identifies when user is answering a follow-up question.
    Setup summary: Mock follow-up message ID and chat history with matching last message, verify True is returned.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                tool.get_followup_question_message_id = AsyncMock(
                    return_value="followup-msg-123"
                )

                mock_message = Mock()
                mock_message.id = "followup-msg-123"
                tool.chat_service.get_full_history_async = AsyncMock(
                    return_value=[mock_message]
                )

                # Act
                result = await tool.is_followup_question_answer()

                # Assert
                assert result is True


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__is_followup_question_answer__returns_false__when_last_message_does_not_match() -> (
    None
):
    """
    Purpose: Verify is_followup_question_answer returns False when last message doesn't match follow-up ID.
    Why this matters: Ensures only matching follow-up questions are identified correctly.
    Setup summary: Mock follow-up message ID and chat history with different last message, verify False is returned.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                tool.get_followup_question_message_id = AsyncMock(
                    return_value="followup-msg-123"
                )

                mock_message = Mock()
                mock_message.id = "different-msg-456"
                tool.chat_service.get_full_history_async = AsyncMock(
                    return_value=[mock_message]
                )

                # Act
                result = await tool.is_followup_question_answer()

                # Assert
                assert result is False


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__update_execution_status__calls_chat_service__with_default_percentage() -> (
    None
):
    """
    Purpose: Verify _update_execution_status calls chat service with default percentage.
    Why this matters: Ensures proper status updates for message execution tracking.
    Setup summary: Mock chat service and call _update_execution_status, verify correct parameters.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                tool.chat_service.update_message_execution_async = AsyncMock()

                # Act
                await tool._update_execution_status(
                    MessageExecutionUpdateStatus.COMPLETED
                )

                # Assert
                tool.chat_service.update_message_execution_async.assert_called_once_with(
                    message_id="test-assistant-message",
                    status="COMPLETED",
                    percentage_completed=100,
                )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__update_execution_status__calls_chat_service__with_custom_percentage() -> (
    None
):
    """
    Purpose: Verify _update_execution_status calls chat service with custom percentage.
    Why this matters: Allows fine-grained progress tracking during execution.
    Setup summary: Mock chat service and call _update_execution_status with custom percentage, verify parameters.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                tool.chat_service.update_message_execution_async = AsyncMock()

                # Act
                await tool._update_execution_status(
                    MessageExecutionUpdateStatus.COMPLETED, percentage=50
                )

                # Assert
                tool.chat_service.update_message_execution_async.assert_called_once_with(
                    message_id="test-assistant-message",
                    status=MessageExecutionUpdateStatus.COMPLETED,
                    percentage_completed=50,
                )


@pytest.mark.ai
def test_deep_research_tool__write_message_log_text_message__calls_create_message_log_entry() -> (
    None
):
    """
    Purpose: Verify write_message_log_text_message calls create_message_log_entry with correct parameters.
    Why this matters: Ensures proper message logging for user feedback.
    Setup summary: Mock create_message_log_entry and call write_message_log_text_message, verify parameters.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                with patch(
                    "unique_deep_research.service.create_message_log_entry"
                ) as mock_create_log:
                    tool = DeepResearchTool(config, mock_event, mock_progress_reporter)

                    # Act
                    tool.write_message_log_text_message("Test log message")

                    # Assert
                    mock_create_log.assert_called_once()
                    args = mock_create_log.call_args
                    assert args[0][0] == tool.chat_service
                    assert args[0][1] == "test-assistant-message"
                    assert args[0][2] == "Test log message"


@pytest.mark.ai
def test_deep_research_tool__get_visible_history_messages__returns_formatted_messages__with_default_count() -> (
    None
):
    """
    Purpose: Verify get_visible_history_messages returns formatted messages with default count.
    Why this matters: Provides properly formatted message history for research brief generation.
    Setup summary: Mock chat service history and call get_visible_history_messages, verify format.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Research AI trends"
    mock_event.payload.user_message.original_text = "Research AI trends"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)

                mock_user_msg = Mock()
                mock_user_msg.role = MockRole("user")
                mock_user_msg.content = "User question"

                mock_assistant_msg = Mock()
                mock_assistant_msg.role = MockRole("assistant")
                mock_assistant_msg.content = "Assistant response"

                tool.chat_service.get_full_history = Mock(
                    return_value=[mock_user_msg, mock_assistant_msg]
                )

                # Act
                result = tool.get_visible_history_messages()

                # Assert
                assert len(result) == 3  # 2 from history + 1 user request
                assert result[0]["role"] == "user"
                assert result[0]["content"] == "User question"
                assert result[1]["role"] == "assistant"
                assert "content" in result[1]
                assert result[1]["content"] == "Assistant response"
                assert result[2]["role"] == "user"
                assert result[2]["content"] == "Research AI trends"


@pytest.mark.ai
def test_deep_research_tool__get_visible_history_messages__returns_formatted_messages__with_custom_count() -> (
    None
):
    """
    Purpose: Verify get_visible_history_messages returns formatted messages with custom count.
    Why this matters: Allows flexible control over how many messages to include in history.
    Setup summary: Mock chat service history and call get_visible_history_messages with custom count, verify format.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Research AI trends"
    mock_event.payload.user_message.original_text = "Research AI trends"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)

                mock_msg1 = Mock()
                mock_msg1.role = MockRole("user")
                mock_msg1.content = "Message 1"

                mock_msg2 = Mock()
                mock_msg2.role = MockRole("assistant")
                mock_msg2.content = "Message 2"

                mock_msg3 = Mock()
                mock_msg3.role = MockRole("user")
                mock_msg3.content = "Message 3"

                tool.chat_service.get_full_history = Mock(
                    return_value=[mock_msg1, mock_msg2, mock_msg3]
                )

                # Act
                result = tool.get_visible_history_messages(messages_to_take=2)

                # Assert
                assert len(result) == 3  # 2 from history + 1 user request
                assert result[0]["role"] == "assistant"
                assert "content" in result[0]
                assert result[0]["content"] == "Message 2"
                assert result[1]["role"] == "user"
                assert result[1]["content"] == "Message 3"
                assert result[2]["role"] == "user"
                assert result[2]["content"] == "Research AI trends"


@pytest.mark.ai
def test_deep_research_tool__tool_description_for_system_prompt__returns_correct_description() -> (
    None
):
    """
    Purpose: Verify tool_description_for_system_prompt returns correct system prompt description.
    Why this matters: System prompt description guides LLM on when to use this tool.
    Setup summary: Create tool and verify system prompt description is correct.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                # Act
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                description = tool.tool_description_for_system_prompt()

                # Assert
                assert "DeepResearch tool is for complex research tasks" in description
                assert "In-depth investigation" in description
                assert "Synthesis of information" in description
                assert "Comprehensive analysis" in description


@pytest.mark.ai
def test_deep_research_tool__evaluation_check_list__returns_hallucination_check() -> (
    None
):
    """
    Purpose: Verify evaluation_check_list returns hallucination evaluation check.
    Why this matters: Ensures research results are evaluated for hallucination.
    Setup summary: Create tool and verify evaluation check list contains hallucination check.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                # Act
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                checks = tool.evaluation_check_list()

                # Assert
                assert len(checks) == 1
                assert "hallucination" in str(checks[0])


@pytest.mark.ai
def test_deep_research_tool__get_evaluation_checks_based_on_tool_response__returns_empty_list__when_no_content_chunks() -> (
    None
):
    """
    Purpose: Verify get_evaluation_checks_based_on_tool_response returns empty list when no content chunks.
    Why this matters: No evaluation needed when tool response has no content to evaluate.
    Setup summary: Create tool response with no content chunks, verify empty list is returned.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                tool_response = ToolCallResponse(
                    id="test-id",
                    name="DeepResearch",
                    content="Test content",
                    content_chunks=[],
                )

                # Act
                checks = tool.get_evaluation_checks_based_on_tool_response(
                    tool_response
                )

                # Assert
                assert checks == []


@pytest.mark.ai
def test_deep_research_tool__get_evaluation_checks_based_on_tool_response__returns_evaluation_list__when_content_chunks_exist() -> (
    None
):
    """
    Purpose: Verify get_evaluation_checks_based_on_tool_response returns evaluation list when content chunks exist.
    Why this matters: Ensures evaluation checks are performed when there's content to evaluate.
    Setup summary: Create tool response with content chunks, verify evaluation list is returned.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                # Create mock ContentChunk objects
                from unique_toolkit.content.schemas import ContentChunk

                mock_chunk1 = ContentChunk(text="chunk1")
                mock_chunk2 = ContentChunk(text="chunk2")

                tool_response = ToolCallResponse(
                    id="test-id",
                    name="DeepResearch",
                    content="Test content",
                    content_chunks=[mock_chunk1, mock_chunk2],
                )

                # Act
                checks = tool.get_evaluation_checks_based_on_tool_response(
                    tool_response
                )

                # Assert
                assert len(checks) == 1
                assert "hallucination" in str(checks[0])


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__run__returns_error_response__when_exception_occurs() -> (
    None
):
    """
    Purpose: Verify run method returns error response when exception occurs.
    Why this matters: Ensures graceful error handling and proper error reporting.
    Setup summary: Mock _run to raise exception, verify error response is returned.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                tool._run = AsyncMock(side_effect=Exception("Test error"))
                tool.chat_service.modify_assistant_message_async = AsyncMock()

                mock_tool_call = Mock()
                mock_tool_call.id = "test-tool-call-id"

                # Act
                result = await tool.run(mock_tool_call)

                # Assert
                assert isinstance(result, ToolCallResponse)
                assert result.id == "test-tool-call-id"
                assert result.name == "DeepResearch"
                assert result.content == "Failed to complete research"
                assert (
                    result.error_message
                    == "Research process failed or returned empty results"
                )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__run__returns_error_response__when_exception_occurs_with_message_execution() -> (
    None
):
    """
    Purpose: Verify run method updates execution status when exception occurs with message execution.
    Why this matters: Ensures proper status tracking even when errors occur.
    Setup summary: Mock _run to raise exception and is_message_execution to return True, verify status update.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = "test-execution-id"
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                tool._run = AsyncMock(side_effect=Exception("Test error"))
                tool._update_execution_status = AsyncMock()
                tool.chat_service.modify_assistant_message_async = AsyncMock()

                mock_tool_call = Mock()
                mock_tool_call.id = "test-tool-call-id"

                # Act
                result = await tool.run(mock_tool_call)

                # Assert
                assert isinstance(result, ToolCallResponse)
                tool._update_execution_status.assert_called_once()
                tool.chat_service.modify_assistant_message_async.assert_called_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__run_research__calls_openai_research__when_engine_is_openai() -> (
    None
):
    """
    Purpose: Verify run_research calls openai_research when engine is OpenAI.
    Why this matters: Ensures correct research method is called based on engine configuration.
    Setup summary: Mock engine type and openai_research method, verify it's called.
    """
    # Arrange
    from unique_deep_research.config import OpenAIEngine

    config = DeepResearchToolConfig(engine=OpenAIEngine())
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                tool.openai_research = AsyncMock(
                    return_value=("research result", ["chunk1"])
                )
                tool.write_message_log_text_message = Mock()

                # Act
                result = await tool.run_research("test brief")

                # Assert
                assert result == ("research result", ["chunk1"])
                tool.openai_research.assert_called_once_with("test brief")
                tool.write_message_log_text_message.assert_called_once_with(
                    "**Research done**"
                )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__run_research__calls_custom_research__when_engine_is_unique() -> (
    None
):
    """
    Purpose: Verify run_research calls custom_research when engine is UNIQUE.
    Why this matters: Ensures correct research method is called based on engine configuration.
    Setup summary: Mock engine type and custom_research method, verify it's called.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                tool.custom_research = AsyncMock(
                    return_value=("custom result", ["chunk1"])
                )
                tool.write_message_log_text_message = Mock()

                # Act
                result = await tool.run_research("test brief")

                # Assert
                assert result == ("custom result", ["chunk1"])
                tool.custom_research.assert_called_once_with("test brief")
                tool.write_message_log_text_message.assert_called_once_with(
                    "**Research done**"
                )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__run_research__returns_empty_result__when_exception_occurs() -> (
    None
):
    """
    Purpose: Verify run_research returns empty result when exception occurs.
    Why this matters: Ensures graceful error handling in research execution.
    Setup summary: Mock research method to raise exception, verify empty result is returned.
    """
    # Arrange
    from unique_deep_research.config import OpenAIEngine

    config = DeepResearchToolConfig(engine=OpenAIEngine())
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                tool.openai_research = AsyncMock(
                    side_effect=Exception("Research failed")
                )
                tool.write_message_log_text_message = Mock()

                # Act
                result = await tool.run_research("test brief")

                # Assert
                assert result == ("", [])
                # When exception occurs, write_message_log_text_message is not called
                tool.write_message_log_text_message.assert_not_called()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__custom_research__returns_processed_result__when_successful() -> (
    None
):
    """
    Purpose: Verify custom_research returns processed result when research is successful.
    Why this matters: Ensures custom research engine produces valid results.
    Setup summary: Mock custom_agent and related services, verify successful result processing.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                with patch("unique_deep_research.service.custom_agent") as mock_agent:
                    with patch(
                        "unique_deep_research.service.GlobalCitationManager"
                    ) as mock_citation_manager:
                        with patch(
                            "unique_deep_research.service.validate_and_map_citations"
                        ) as mock_validate:
                            tool = DeepResearchTool(
                                config, mock_event, mock_progress_reporter
                            )

                            # Mock agent result
                            mock_agent.ainvoke = AsyncMock(
                                return_value={"final_report": "Test research report"}
                            )

                            # Mock citation manager
                            mock_citation_instance = Mock()
                            mock_citation_instance.get_all_citations.return_value = []
                            mock_citation_manager.return_value = mock_citation_instance

                            # Mock validation
                            mock_validate.return_value = ("Processed report", [])

                            tool.chat_service.modify_assistant_message_async = (
                                AsyncMock()
                            )

                            # Act
                            result = await tool.custom_research("test brief")

                            # Assert
                            assert result == ("Processed report", [])
                            mock_agent.ainvoke.assert_called_once()
                            mock_validate.assert_called_once_with(
                                "Test research report", []
                            )
                            tool.chat_service.modify_assistant_message_async.assert_called_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__custom_research__returns_empty_result__when_no_final_report() -> (
    None
):
    """
    Purpose: Verify custom_research returns empty result when no final report is generated.
    Why this matters: Ensures graceful handling when research doesn't produce results.
    Setup summary: Mock custom_agent to return empty final_report, verify empty result.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                with patch("unique_deep_research.service.custom_agent") as mock_agent:
                    with patch(
                        "unique_deep_research.service.GlobalCitationManager"
                    ) as mock_citation_manager:
                        tool = DeepResearchTool(
                            config, mock_event, mock_progress_reporter
                        )

                        # Mock agent result with empty final_report
                        mock_agent.ainvoke = AsyncMock(
                            return_value={"final_report": ""}
                        )

                        # Mock citation manager
                        mock_citation_instance = Mock()
                        mock_citation_manager.return_value = mock_citation_instance

                        # Act
                        result = await tool.custom_research("test brief")

                        # Assert
                        assert result == ("", [])


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__custom_research__returns_error_message__when_exception_occurs() -> (
    None
):
    """
    Purpose: Verify custom_research returns error message when exception occurs.
    Why this matters: Ensures proper error handling and reporting in custom research.
    Setup summary: Mock custom_agent to raise exception, verify error message is returned.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                with patch("unique_deep_research.service.custom_agent") as mock_agent:
                    with patch(
                        "unique_deep_research.service.GlobalCitationManager"
                    ) as mock_citation_manager:
                        tool = DeepResearchTool(
                            config, mock_event, mock_progress_reporter
                        )

                        # Mock agent to raise exception
                        mock_agent.ainvoke = AsyncMock(
                            side_effect=Exception("Custom research failed")
                        )

                        # Mock citation manager
                        mock_citation_instance = Mock()
                        mock_citation_manager.return_value = mock_citation_instance

                        # Act
                        result = await tool.custom_research("test brief")

                        # Assert
                        assert (
                            result[0]
                            == "Custom research failed: Custom research failed"
                        )
                        assert result[1] == []


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__openai_research__returns_processed_result__when_successful() -> (
    None
):
    """
    Purpose: Verify openai_research returns processed result when research is successful.
    Why this matters: Ensures OpenAI research engine produces valid results.
    Setup summary: Mock OpenAI client and related services, verify successful result processing.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                with patch(
                    "unique_deep_research.service.postprocess_research_result_with_chunks"
                ) as mock_postprocess:
                    with patch("unique_deep_research.service.crawl_url"):
                        tool = DeepResearchTool(
                            config, mock_event, mock_progress_reporter
                        )

                        # Mock OpenAI client responses
                        mock_stream = AsyncMock()
                        mock_stream.__aiter__ = AsyncMock(return_value=iter([]))
                        tool.client.responses.create = AsyncMock(
                            return_value=mock_stream
                        )

                        # Mock postprocessing
                        mock_postprocess.return_value = (
                            "Processed result",
                            [],
                            ["chunk1"],
                        )

                        # Mock report postprocessing
                        tool._postprocess_report_with_gpt = AsyncMock(
                            return_value="Final report"
                        )
                        tool._convert_annotations_to_references = Mock(return_value=[])
                        tool.chat_service.modify_assistant_message_async = AsyncMock()

                        # Mock stream processing
                        tool._process_research_stream = AsyncMock(
                            return_value=("Raw result", [])
                        )

                        # Act
                        result = await tool.openai_research("test brief")

                        # Assert
                        assert result == ("Final report", ["chunk1"])
                        tool.client.responses.create.assert_called_once()
                        mock_postprocess.assert_called_once()
                        tool._postprocess_report_with_gpt.assert_called_once_with(
                            "Processed result"
                        )
                        tool.chat_service.modify_assistant_message_async.assert_called_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__openai_research__returns_empty_result__when_no_research_result() -> (
    None
):
    """
    Purpose: Verify openai_research returns empty result when no research result is generated.
    Why this matters: Ensures graceful handling when OpenAI research doesn't produce results.
    Setup summary: Mock stream processing to return empty result, verify empty result.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)

                # Mock OpenAI client responses
                mock_stream = AsyncMock()
                mock_stream.__aiter__ = AsyncMock(return_value=iter([]))
                tool.client.responses.create = AsyncMock(return_value=mock_stream)

                # Mock stream processing to return empty result
                tool._process_research_stream = AsyncMock(return_value=("", []))

                # Act
                result = await tool.openai_research("test brief")

                # Assert
                assert result == ("", [])


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__postprocess_report_with_gpt__returns_formatted_result__when_successful() -> (
    None
):
    """
    Purpose: Verify _postprocess_report_with_gpt returns formatted result when successful.
    Why this matters: Ensures research reports are properly formatted for readability.
    Setup summary: Mock GPT completion and template rendering, verify formatted result.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)

                # Mock GPT completion
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = "Formatted report"
                tool.client.chat.completions.create = AsyncMock(
                    return_value=mock_response
                )

                # Mock template rendering
                mock_template = Mock()
                mock_template.render.return_value = "Template content"
                with patch.object(tool.env, "get_template", return_value=mock_template):
                    tool.write_message_log_text_message = Mock()

                    # Act
                    result = await tool._postprocess_report_with_gpt("Raw report")

                    # Assert
                    assert result == "Formatted report"
                    tool.client.chat.completions.create.assert_called_once()
                    tool.write_message_log_text_message.assert_called_once_with(
                        "**Synthesizing final research report**"
                    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__postprocess_report_with_gpt__returns_original_result__when_gpt_returns_empty() -> (
    None
):
    """
    Purpose: Verify _postprocess_report_with_gpt returns original result when GPT returns empty.
    Why this matters: Ensures fallback to original content when formatting fails.
    Setup summary: Mock GPT completion to return empty content, verify original result is returned.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)

                # Mock GPT completion with empty content
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = None
                tool.client.chat.completions.create = AsyncMock(
                    return_value=mock_response
                )

                # Mock template rendering
                mock_template = Mock()
                mock_template.render.return_value = "Template content"
                with patch.object(tool.env, "get_template", return_value=mock_template):
                    tool.write_message_log_text_message = Mock()

                    # Act
                    result = await tool._postprocess_report_with_gpt("Raw report")

                    # Assert
                    assert result == "Raw report"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__clarify_user_request__returns_clarifying_questions__when_successful() -> (
    None
):
    """
    Purpose: Verify clarify_user_request returns clarifying questions when successful.
    Why this matters: Ensures proper clarification of user research requests.
    Setup summary: Mock chat service completion and template rendering, verify questions are returned.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)

                # Mock chat service completion
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[
                    0
                ].message.content = (
                    "What specific aspect of AI trends are you interested in?"
                )
                tool.chat_service.complete_async = AsyncMock(return_value=mock_response)

                # Mock template rendering
                mock_template = Mock()
                mock_template.render.return_value = "Template content"
                with patch.object(tool.env, "get_template", return_value=mock_template):
                    # Mock get_visible_history_messages
                    tool.get_visible_history_messages = Mock(
                        return_value=[{"role": "user", "content": "Test"}]
                    )

                    # Act
                    result = await tool.clarify_user_request()

                    # Assert
                    assert (
                        result
                        == "What specific aspect of AI trends are you interested in?"
                    )
                    tool.chat_service.complete_async.assert_called_once()
                    tool.get_visible_history_messages.assert_called_once_with(4)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__generate_research_brief_from_dict__returns_research_instructions__when_successful() -> (
    None
):
    """
    Purpose: Verify generate_research_brief_from_dict returns research instructions when successful.
    Why this matters: Ensures proper research brief generation from message history.
    Setup summary: Mock OpenAI client completion and template rendering, verify instructions are returned.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)

                # Mock OpenAI client completion
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[
                    0
                ].message.content = "Research instructions for AI trends"
                tool.client.chat.completions.create = AsyncMock(
                    return_value=mock_response
                )

                # Mock template rendering
                mock_template = Mock()
                mock_template.render.return_value = "Template content"
                with patch.object(tool.env, "get_template", return_value=mock_template):
                    messages = [{"role": "user", "content": "Research AI trends"}]

                    # Act
                    result = await tool.generate_research_brief_from_dict(messages)

                    # Assert
                    assert result == "Research instructions for AI trends"
                    tool.client.chat.completions.create.assert_called_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__generate_research_brief__returns_research_instructions__when_successful() -> (
    None
):
    """
    Purpose: Verify generate_research_brief returns research instructions when successful.
    Why this matters: Ensures proper research brief generation from LanguageModelMessage objects.
    Setup summary: Mock generate_research_brief_from_dict, verify instructions are returned.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)

                # Mock generate_research_brief_from_dict
                tool.generate_research_brief_from_dict = AsyncMock(
                    return_value="Research instructions"
                )

                # Create mock LanguageModelMessage objects
                mock_message1 = Mock()
                mock_message1.content = "User question"
                mock_message1.role.value = "user"

                mock_message2 = Mock()
                mock_message2.content = "Assistant response"
                mock_message2.role.value = "assistant"

                messages = [mock_message1, mock_message2]

                # Act
                result = await tool.generate_research_brief(messages)

                # Assert
                assert result == "Research instructions"
                tool.generate_research_brief_from_dict.assert_called_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__generate_research_brief__handles_role_without_value__when_successful() -> (
    None
):
    """
    Purpose: Verify generate_research_brief handles role without value attribute when successful.
    Why this matters: Ensures compatibility with different role object types.
    Setup summary: Mock message with role that doesn't have value attribute, verify proper handling.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)

                # Mock generate_research_brief_from_dict
                tool.generate_research_brief_from_dict = AsyncMock(
                    return_value="Research instructions"
                )

                # Create mock LanguageModelMessage with role without value
                mock_message = Mock()
                mock_message.content = "User question"
                mock_message.role = "user"  # String role instead of object with value

                messages = [mock_message]

                # Act
                result = await tool.generate_research_brief(messages)

                # Assert
                assert result == "Research instructions"
                tool.generate_research_brief_from_dict.assert_called_once()


@pytest.mark.ai
def test_deep_research_tool__convert_annotations_to_references__returns_content_references__when_successful() -> (
    None
):
    """
    Purpose: Verify _convert_annotations_to_references returns ContentReference objects when successful.
    Why this matters: Ensures proper conversion of OpenAI annotations to content references.
    Setup summary: Mock annotations and verify ContentReference objects are created.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)

                # Create mock annotations that pass isinstance check
                from openai.types.responses.response_output_text import (
                    AnnotationURLCitation,
                )

                mock_annotation1 = Mock(spec=AnnotationURLCitation)
                mock_annotation1.title = "Test Article 1"
                mock_annotation1.url = "https://example.com/article1"

                mock_annotation2 = Mock(spec=AnnotationURLCitation)
                mock_annotation2.title = "Test Article 2"
                mock_annotation2.url = "https://example.com/article2"

                annotations = [mock_annotation1, mock_annotation2]

                # Act
                result = tool._convert_annotations_to_references(
                    annotations, "test-message-id"
                )

                # Assert
                assert len(result) == 2
                assert result[0].message_id == "test-message-id"
                assert result[0].name == "Test Article 1"
                assert result[0].url == "https://example.com/article1"
                assert result[0].sequence_number == 1
                assert result[0].source == "deep-research-citations"
                assert result[0].source_id == "https://example.com/article1"

                assert result[1].message_id == "test-message-id"
                assert result[1].name == "Test Article 2"
                assert result[1].url == "https://example.com/article2"
                assert result[1].sequence_number == 2
                assert result[1].source == "deep-research-citations"
                assert result[1].source_id == "https://example.com/article2"


@pytest.mark.ai
def test_deep_research_tool__convert_annotations_to_references__returns_content_references__with_default_message_id() -> (
    None
):
    """
    Purpose: Verify _convert_annotations_to_references uses default message_id when none provided.
    Why this matters: Ensures proper fallback for message_id in content references.
    Setup summary: Mock annotations without message_id, verify default is used.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)

                # Create mock annotation that passes isinstance check
                from openai.types.responses.response_output_text import (
                    AnnotationURLCitation,
                )

                mock_annotation = Mock(spec=AnnotationURLCitation)
                mock_annotation.title = "Test Article"
                mock_annotation.url = "https://example.com/article"

                annotations = [mock_annotation]

                # Act
                result = tool._convert_annotations_to_references(annotations)

                # Assert
                assert len(result) == 1
                assert result[0].message_id == ""
                assert result[0].name == "Test Article"
                assert result[0].url == "https://example.com/article"


@pytest.mark.ai
def test_deep_research_tool__convert_annotations_to_references__skips_non_url_citations__when_filtering() -> (
    None
):
    """
    Purpose: Verify _convert_annotations_to_references skips non-URL citations when filtering.
    Why this matters: Ensures only valid URL citations are converted to references.
    Setup summary: Mock annotations with mixed types, verify only URL citations are processed.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)

                # Create mock annotations with different types
                from openai.types.responses.response_output_text import (
                    AnnotationURLCitation,
                )

                mock_url_annotation = Mock(spec=AnnotationURLCitation)
                mock_url_annotation.title = "URL Article"
                mock_url_annotation.url = "https://example.com/article"

                mock_non_url_annotation = Mock()  # This won't pass isinstance check
                mock_non_url_annotation.title = "Non-URL Annotation"

                annotations = [mock_url_annotation, mock_non_url_annotation]

                # Act
                result = tool._convert_annotations_to_references(annotations)

                # Assert
                assert len(result) == 1
                assert result[0].name == "URL Article"
                assert result[0].url == "https://example.com/article"

@pytest.mark.ai
@pytest.mark.asyncio
async def test_deep_research_tool__update_tool_debug_info__calls_chat_service__with_correct_debug_info() -> (
    None
):
    """
    Purpose: Verify _update_tool_debug_info calls chat service with correct debug info.
    Why this matters: Ensures debug info is properly logged for tool execution tracking.
    Setup summary: Mock chat service and call _update_tool_debug_info, verify correct parameters.
    """
    # Arrange
    config = DeepResearchToolConfig()
    mock_event = Mock()
    mock_event.company_id = "test-company"
    mock_event.user_id = "test-user"
    mock_event.payload.chat_id = "test-chat"
    mock_event.payload.assistant_message.id = "test-assistant-message"
    mock_event.payload.user_message.text = "Test request"
    mock_event.payload.user_message.original_text = "Test request"
    mock_event.payload.message_execution_id = None
    mock_event.payload.assistant_id = "test-assistant-id"
    mock_event.payload.name = "Test Assistant"
    mock_event.payload.user_metadata = {"key": "value"}
    mock_event.payload.tool_parameters = {"param": "test"}
    mock_progress_reporter = Mock()

    with patch("unique_deep_research.service.get_async_openai_client"):
        with patch("unique_deep_research.service.ContentService"):
            with patch("unique_toolkit.agentic.tools.tool.LanguageModelService"):
                tool = DeepResearchTool(config, mock_event, mock_progress_reporter)
                tool.chat_service.update_debug_info_async = AsyncMock()

                # Act
                await tool._update_tool_debug_info()

                # Assert
                tool.chat_service.update_debug_info_async.assert_called_once()
                call_args = tool.chat_service.update_debug_info_async.call_args
                debug_info = call_args.kwargs["debug_info"]

                assert debug_info["tools"] == [
                    {
                        "name": "DeepResearch",
                        "info": {
                            "is_forced": True,
                            "is_exclusive": True,
                            "loop_iteration": 0,
                        },
                    }
                ]
                assert debug_info["assistant"] == {
                    "id": "test-assistant-id",
                    "name": "Test Assistant",
                }
                assert debug_info["chosenModule"] == "Test Assistant"
                assert debug_info["userMetadata"] == {"key": "value"}
                assert debug_info["toolParameters"] == {"param": "test"}
