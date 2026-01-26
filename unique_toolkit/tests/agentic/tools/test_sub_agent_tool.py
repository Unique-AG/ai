from unittest.mock import AsyncMock, Mock, patch

import pytest

from unique_toolkit.agentic.feature_flags import FeatureFlags
from unique_toolkit.agentic.tools.a2a.tool.config import SubAgentToolConfig
from unique_toolkit.agentic.tools.a2a.tool.service import SubAgentTool
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ProgressState,
    ToolProgressReporter,
)
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.schemas import MessageLogStatus
from unique_toolkit.language_model.schemas import LanguageModelFunction


@pytest.fixture
def mock_chat_event() -> ChatEvent:
    """Create a mock ChatEvent for testing."""
    event = Mock(spec=ChatEvent)
    event.user_id = "user_123"
    event.company_id = "company_456"
    event.chat_id = "chat_789"
    event.assistant_id = "assistant_101"

    # Mock the payload structure
    mock_payload = Mock()
    mock_payload.chat_id = "chat_789"
    mock_payload.assistant_message = Mock()
    mock_payload.assistant_message.id = "assistant_message_202"
    event.payload = mock_payload

    return event


@pytest.fixture
def mock_sub_agent_config() -> SubAgentToolConfig:
    """Create a mock SubAgentToolConfig for testing."""
    return SubAgentToolConfig(
        assistant_id="sub_agent_assistant_123",
        tool_description="A test sub agent tool",
        tool_description_for_system_prompt="System prompt for sub agent",
        tool_format_information_for_system_prompt="Format info for system prompt",
        tool_description_for_user_prompt="User prompt for sub agent",
        tool_format_information_for_user_prompt="Format info for user prompt",
        param_description_sub_agent_user_message="Message to send to sub agent",
    )


@pytest.fixture
def sub_agent_tool(
    mock_sub_agent_config: SubAgentToolConfig,
    mock_chat_event: ChatEvent,
) -> SubAgentTool:
    """Create a SubAgentTool instance for testing."""
    return SubAgentTool(
        configuration=mock_sub_agent_config,
        event=mock_chat_event,
        name="TestSubAgent",
        display_name="Test Sub Agent",
    )


class TestSubAgentToolInitialization:
    """Test suite for SubAgentTool initialization."""

    @pytest.mark.ai
    def test_init__sets_correct_attributes__with_valid_inputs_AI(
        self,
        mock_sub_agent_config: SubAgentToolConfig,
        mock_chat_event: ChatEvent,
    ) -> None:
        """
        Purpose: Verify that SubAgentTool initializes with correct attributes.
        Why this matters: Proper initialization ensures the tool has access to all necessary data.
        Setup summary: Create tool with mocks, verify attributes are set correctly.
        """
        # Act
        tool = SubAgentTool(
            configuration=mock_sub_agent_config,
            event=mock_chat_event,
            name="TestSubAgent",
            display_name="Test Sub Agent",
        )

        # Assert
        assert tool.name == "TestSubAgent"
        assert tool._display_name == "Test Sub Agent"
        assert tool._user_id == "user_123"
        assert tool._company_id == "company_456"
        assert tool._active_message_log is None

#     @pytest.mark.ai
#     def test_init__accepts_optional_progress_reporter__with_reporter_AI(
#         self,
#         mock_sub_agent_config: SubAgentToolConfig,
#         mock_chat_event: ChatEvent,
#     ) -> None:
#         """
#         Purpose: Verify that SubAgentTool can be initialized with a progress reporter.
#         Why this matters: Progress reporting is optional but important for user feedback.
#         Setup summary: Create tool with mock progress reporter, verify it's stored.
#         """
#         # Arrange
#         mock_progress_reporter = Mock(spec=ToolProgressReporter)

#         # Act
#         tool = SubAgentTool(
#             configuration=mock_sub_agent_config,
#             event=mock_chat_event,
#             tool_progress_reporter=mock_progress_reporter,
#             name="TestSubAgent",
#             display_name="Test Sub Agent",
#         )

#         # Assert
#         assert tool.tool_progress_reporter == mock_progress_reporter


# class TestSubAgentToolDescription:
#     """Test suite for tool description methods."""

#     @pytest.mark.ai
#     def test_display_name__returns_configured_name__AI(
#         self,
#         sub_agent_tool: SubAgentTool,
#     ) -> None:
#         """
#         Purpose: Verify display_name returns the configured display name.
#         Why this matters: Display names are shown to users in the UI.
#         Setup summary: Call display_name, verify it returns expected value.
#         """
#         # Act
#         name = sub_agent_tool.display_name()

#         # Assert
#         assert name == "Test Sub Agent"

#     @pytest.mark.ai
#     def test_tool_description_for_system_prompt__returns_config_value__AI(
#         self,
#         sub_agent_tool: SubAgentTool,
#     ) -> None:
#         """
#         Purpose: Verify tool_description_for_system_prompt returns config value.
#         Why this matters: System prompts provide context to LLMs.
#         Setup summary: Call method, verify it returns the configured value.
#         """
#         # Act
#         system_prompt = sub_agent_tool.tool_description_for_system_prompt()

#         # Assert
#         assert system_prompt == "System prompt for sub agent"

#     @pytest.mark.ai
#     def test_tool_description_for_user_prompt__returns_config_value__AI(
#         self,
#         sub_agent_tool: SubAgentTool,
#     ) -> None:
#         """
#         Purpose: Verify tool_description_for_user_prompt returns config value.
#         Why this matters: User prompts provide guidance on tool usage.
#         Setup summary: Call method, verify it returns the configured value.
#         """
#         # Act
#         user_prompt = sub_agent_tool.tool_description_for_user_prompt()

#         # Assert
#         assert user_prompt == "User prompt for sub agent"

#     @pytest.mark.ai
#     def test_tool_format_information_for_system_prompt__returns_config_value__AI(
#         self,
#         sub_agent_tool: SubAgentTool,
#     ) -> None:
#         """
#         Purpose: Verify tool_format_information_for_system_prompt returns config value.
#         Why this matters: Format information guides LLMs on output structure.
#         Setup summary: Call method, verify it returns the configured value.
#         """
#         # Act
#         format_info = sub_agent_tool.tool_format_information_for_system_prompt()

#         # Assert
#         assert format_info == "Format info for system prompt"

#     @pytest.mark.ai
#     def test_tool_format_information_for_user_prompt__returns_config_value__AI(
#         self,
#         sub_agent_tool: SubAgentTool,
#     ) -> None:
#         """
#         Purpose: Verify tool_format_information_for_user_prompt returns config value.
#         Why this matters: Format information for user prompt.
#         Setup summary: Call method, verify it returns the configured value.
#         """
#         # Act
#         format_info = sub_agent_tool.tool_format_information_for_user_prompt()

#         # Assert
#         assert format_info == "Format info for user prompt"


# class TestSubAgentToolProgressNotifications:
#     """Test suite for progress notification behavior based on feature flag."""

#     @pytest.mark.ai
#     @pytest.mark.asyncio
#     async def test_notify_progress__sends_notification__when_new_ui_disabled_AI(
#         self,
#         mock_sub_agent_config: SubAgentToolConfig,
#         mock_chat_event: ChatEvent,
#     ) -> None:
#         """
#         Purpose: Verify progress notifications are sent when new UI is disabled.
#         Why this matters: Legacy UI relies on progress notifications for user feedback.
#         Setup summary: Create tool with mock reporter, mock feature flag to return False, verify notifications.
#         """
#         # Arrange
#         mock_progress_reporter = Mock(spec=ToolProgressReporter)
#         mock_progress_reporter.notify_from_tool_call = AsyncMock()

#         tool = SubAgentTool(
#             configuration=mock_sub_agent_config,
#             event=mock_chat_event,
#             tool_progress_reporter=mock_progress_reporter,
#             name="TestSubAgent",
#             display_name="Test Sub Agent",
#         )

#         tool_call = LanguageModelFunction(
#             id="call_123",
#             name="TestSubAgent",
#             arguments={"user_message": "test message"},
#         )

#         with patch.object(
#             FeatureFlags,
#             "is_new_answers_ui_enabled",
#             return_value=False,
#         ):
#             # Act
#             await tool._notify_progress(
#                 tool_call=tool_call,
#                 message="Test progress message",
#                 state=ProgressState.RUNNING,
#             )

#             # Assert
#             mock_progress_reporter.notify_from_tool_call.assert_called_once_with(
#                 tool_call=tool_call,
#                 name="Test Sub Agent",
#                 message="Test progress message",
#                 state=ProgressState.RUNNING,
#             )

#     @pytest.mark.ai
#     @pytest.mark.asyncio
#     async def test_notify_progress__skips_notification__when_new_ui_enabled_AI(
#         self,
#         mock_sub_agent_config: SubAgentToolConfig,
#         mock_chat_event: ChatEvent,
#     ) -> None:
#         """
#         Purpose: Verify progress notifications are NOT sent when new UI is enabled.
#         Why this matters: New UI has different progress tracking mechanism.
#         Setup summary: Create tool with mock reporter, mock feature flag to return True, verify no notifications.
#         """
#         # Arrange
#         mock_progress_reporter = Mock(spec=ToolProgressReporter)
#         mock_progress_reporter.notify_from_tool_call = AsyncMock()

#         tool = SubAgentTool(
#             configuration=mock_sub_agent_config,
#             event=mock_chat_event,
#             tool_progress_reporter=mock_progress_reporter,
#             name="TestSubAgent",
#             display_name="Test Sub Agent",
#         )

#         tool_call = LanguageModelFunction(
#             id="call_123",
#             name="TestSubAgent",
#             arguments={"user_message": "test message"},
#         )

#         with patch.object(
#             FeatureFlags,
#             "is_new_answers_ui_enabled",
#             return_value=True,
#         ):
#             # Act
#             await tool._notify_progress(
#                 tool_call=tool_call,
#                 message="Test progress message",
#                 state=ProgressState.RUNNING,
#             )

#             # Assert - progress reporter should NOT be called
#             mock_progress_reporter.notify_from_tool_call.assert_not_called()

#     @pytest.mark.ai
#     @pytest.mark.asyncio
#     async def test_notify_progress__skips_when_no_reporter__AI(
#         self,
#         sub_agent_tool: SubAgentTool,
#     ) -> None:
#         """
#         Purpose: Verify no error when progress reporter is not set.
#         Why this matters: Progress reporter is optional functionality.
#         Setup summary: Create tool without reporter, call _notify_progress, verify no error.
#         """
#         # Arrange
#         tool_call = LanguageModelFunction(
#             id="call_123",
#             name="TestSubAgent",
#             arguments={"user_message": "test message"},
#         )

#         # Act - should not raise any exception
#         await sub_agent_tool._notify_progress(
#             tool_call=tool_call,
#             message="Test progress message",
#             state=ProgressState.RUNNING,
#         )

#         # Assert - no exception was raised

#     @pytest.mark.ai
#     @pytest.mark.asyncio
#     async def test_notify_progress__checks_feature_flag_with_company_id__AI(
#         self,
#         mock_sub_agent_config: SubAgentToolConfig,
#         mock_chat_event: ChatEvent,
#     ) -> None:
#         """
#         Purpose: Verify feature flag is checked with the correct company_id from the event.
#         Why this matters: Feature flags are company-specific.
#         Setup summary: Create tool, call _notify_progress, verify feature flag is called with correct company_id.
#         """
#         # Arrange
#         mock_progress_reporter = Mock(spec=ToolProgressReporter)
#         mock_progress_reporter.notify_from_tool_call = AsyncMock()

#         tool = SubAgentTool(
#             configuration=mock_sub_agent_config,
#             event=mock_chat_event,
#             tool_progress_reporter=mock_progress_reporter,
#             name="TestSubAgent",
#             display_name="Test Sub Agent",
#         )

#         tool_call = LanguageModelFunction(
#             id="call_123",
#             name="TestSubAgent",
#             arguments={"user_message": "test message"},
#         )

#         with patch.object(
#             FeatureFlags,
#             "is_new_answers_ui_enabled",
#             return_value=False,
#         ) as mock_feature_flag:
#             # Act
#             await tool._notify_progress(
#                 tool_call=tool_call,
#                 message="Test progress message",
#                 state=ProgressState.RUNNING,
#             )

#             # Assert - feature flag should be called with the company_id from the event
#             mock_feature_flag.assert_called_with("company_456")


# class TestSubAgentToolMessageLog:
#     """Test suite for message log behavior using create_or_update pattern."""

#     @pytest.mark.ai
#     def test_create_or_update_message_log__creates_new_log__when_none_exists_AI(
#         self,
#         mock_sub_agent_config: SubAgentToolConfig,
#         mock_chat_event: ChatEvent,
#     ) -> None:
#         """
#         Purpose: Verify message log is created when none exists.
#         Why this matters: First call should create a new log entry.
#         Setup summary: Create tool with mocked logger, call _create_or_update_message_log, verify create_or_update is called.
#         """
#         # Arrange
#         tool = SubAgentTool(
#             configuration=mock_sub_agent_config,
#             event=mock_chat_event,
#             name="TestSubAgent",
#             display_name="Test Sub Agent",
#         )

#         mock_message_log = Mock()
#         tool._message_step_logger = Mock()
#         tool._message_step_logger.create_or_update_message_log = Mock(
#             return_value=mock_message_log
#         )

#         # Act
#         tool._create_or_update_message_log(
#             progress_message="_Running sub agent_",
#             status=MessageLogStatus.RUNNING,
#         )

#         # Assert
#         tool._message_step_logger.create_or_update_message_log.assert_called_once_with(
#             active_message_log=None,
#             header="Test Sub Agent",
#             progress_message="_Running sub agent_",
#             status=MessageLogStatus.RUNNING,
#         )
#         assert tool._active_message_log == mock_message_log

#     @pytest.mark.ai
#     def test_create_or_update_message_log__updates_existing_log__when_exists_AI(
#         self,
#         mock_sub_agent_config: SubAgentToolConfig,
#         mock_chat_event: ChatEvent,
#     ) -> None:
#         """
#         Purpose: Verify message log is updated when one already exists.
#         Why this matters: Subsequent calls should update the existing log entry.
#         Setup summary: Create tool with existing log, call _create_or_update_message_log, verify update is called with existing log.
#         """
#         # Arrange
#         tool = SubAgentTool(
#             configuration=mock_sub_agent_config,
#             event=mock_chat_event,
#             name="TestSubAgent",
#             display_name="Test Sub Agent",
#         )

#         existing_log = Mock()
#         updated_log = Mock()
#         tool._active_message_log = existing_log
#         tool._message_step_logger = Mock()
#         tool._message_step_logger.create_or_update_message_log = Mock(
#             return_value=updated_log
#         )

#         # Act
#         tool._create_or_update_message_log(
#             progress_message="_Finished_",
#             status=MessageLogStatus.COMPLETED,
#         )

#         # Assert
#         tool._message_step_logger.create_or_update_message_log.assert_called_once_with(
#             active_message_log=existing_log,
#             header="Test Sub Agent",
#             progress_message="_Finished_",
#             status=MessageLogStatus.COMPLETED,
#         )
#         assert tool._active_message_log == updated_log


# class TestSubAgentToolRun:
#     """Test suite for tool execution."""

#     @pytest.mark.ai
#     @pytest.mark.asyncio
#     async def test_run__sends_progress_notifications__when_new_ui_disabled_AI(
#         self,
#         mock_sub_agent_config: SubAgentToolConfig,
#         mock_chat_event: ChatEvent,
#     ) -> None:
#         """
#         Purpose: Verify run() sends progress notifications when new UI is disabled.
#         Why this matters: Full integration test of progress reporting in the run method.
#         Setup summary: Mock all dependencies, execute run, verify progress notifications were sent.
#         """
#         # Arrange
#         mock_progress_reporter = Mock(spec=ToolProgressReporter)
#         mock_progress_reporter.notify_from_tool_call = AsyncMock()

#         mock_response_watcher = Mock()
#         mock_response_watcher.notify_response = Mock()

#         tool = SubAgentTool(
#             configuration=mock_sub_agent_config,
#             event=mock_chat_event,
#             tool_progress_reporter=mock_progress_reporter,
#             name="TestSubAgent",
#             display_name="Test Sub Agent",
#             response_watcher=mock_response_watcher,
#         )

#         # Mock the message step logger
#         mock_message_log = Mock()
#         tool._message_step_logger = Mock()
#         tool._message_step_logger.create_or_update_message_log = Mock(
#             return_value=mock_message_log
#         )

#         tool_call = LanguageModelFunction(
#             id="call_123",
#             name="TestSubAgent",
#             arguments={"user_message": "test message"},
#         )

#         mock_response = {
#             "text": "Sub agent response",
#             "assessment": None,
#             "chatId": "new_chat_id",
#             "references": None,
#         }

#         with (
#             patch.object(
#                 FeatureFlags,
#                 "is_new_answers_ui_enabled",
#                 return_value=False,
#             ),
#             patch(
#                 "unique_toolkit.agentic.tools.a2a.tool.service.send_message_and_wait_for_completion",
#                 new_callable=AsyncMock,
#                 return_value=mock_response,
#             ),
#             patch.object(
#                 tool, "_get_chat_id", new_callable=AsyncMock, return_value=None
#             ),
#             patch.object(
#                 tool, "_save_chat_id", new_callable=AsyncMock, return_value=None
#             ),
#         ):
#             # Act
#             await tool.run(tool_call)

#             # Assert - progress reporter should have been called at least twice (RUNNING and FINISHED)
#             assert mock_progress_reporter.notify_from_tool_call.call_count >= 2

#             # Check for RUNNING state
#             running_calls = [
#                 call
#                 for call in mock_progress_reporter.notify_from_tool_call.call_args_list
#                 if call.kwargs.get("state") == ProgressState.RUNNING
#             ]
#             assert len(running_calls) >= 1

#             # Check for FINISHED state
#             finished_calls = [
#                 call
#                 for call in mock_progress_reporter.notify_from_tool_call.call_args_list
#                 if call.kwargs.get("state") == ProgressState.FINISHED
#             ]
#             assert len(finished_calls) == 1

#     @pytest.mark.ai
#     @pytest.mark.asyncio
#     async def test_run__skips_progress_notifications__when_new_ui_enabled_AI(
#         self,
#         mock_sub_agent_config: SubAgentToolConfig,
#         mock_chat_event: ChatEvent,
#     ) -> None:
#         """
#         Purpose: Verify run() skips progress notifications when new UI is enabled.
#         Why this matters: New UI has different progress tracking mechanism.
#         Setup summary: Mock all dependencies, execute run, verify no progress notifications were sent.
#         """
#         # Arrange
#         mock_progress_reporter = Mock(spec=ToolProgressReporter)
#         mock_progress_reporter.notify_from_tool_call = AsyncMock()

#         mock_response_watcher = Mock()
#         mock_response_watcher.notify_response = Mock()

#         tool = SubAgentTool(
#             configuration=mock_sub_agent_config,
#             event=mock_chat_event,
#             tool_progress_reporter=mock_progress_reporter,
#             name="TestSubAgent",
#             display_name="Test Sub Agent",
#             response_watcher=mock_response_watcher,
#         )

#         # Mock the message step logger
#         mock_message_log = Mock()
#         tool._message_step_logger = Mock()
#         tool._message_step_logger.create_or_update_message_log = Mock(
#             return_value=mock_message_log
#         )

#         tool_call = LanguageModelFunction(
#             id="call_123",
#             name="TestSubAgent",
#             arguments={"user_message": "test message"},
#         )

#         mock_response = {
#             "text": "Sub agent response",
#             "assessment": None,
#             "chatId": "new_chat_id",
#             "references": None,
#         }

#         with (
#             patch.object(
#                 FeatureFlags,
#                 "is_new_answers_ui_enabled",
#                 return_value=True,
#             ),
#             patch(
#                 "unique_toolkit.agentic.tools.a2a.tool.service.send_message_and_wait_for_completion",
#                 new_callable=AsyncMock,
#                 return_value=mock_response,
#             ),
#             patch.object(
#                 tool, "_get_chat_id", new_callable=AsyncMock, return_value=None
#             ),
#             patch.object(
#                 tool, "_save_chat_id", new_callable=AsyncMock, return_value=None
#             ),
#         ):
#             # Act
#             response = await tool.run(tool_call)

#             # Assert - tool should still execute successfully
#             assert response.name == "TestSubAgent"
#             assert "Sub agent response" in response.content

#             # But progress reporter should NOT be called
#             mock_progress_reporter.notify_from_tool_call.assert_not_called()

#     @pytest.mark.ai
#     @pytest.mark.asyncio
#     async def test_run__updates_message_log__on_successful_execution_AI(
#         self,
#         mock_sub_agent_config: SubAgentToolConfig,
#         mock_chat_event: ChatEvent,
#     ) -> None:
#         """
#         Purpose: Verify run() updates message log to COMPLETED on successful execution.
#         Why this matters: Message log should reflect the final state of the tool execution.
#         Setup summary: Mock all dependencies, execute run, verify message log is updated to COMPLETED.
#         """
#         # Arrange
#         mock_response_watcher = Mock()
#         mock_response_watcher.notify_response = Mock()

#         tool = SubAgentTool(
#             configuration=mock_sub_agent_config,
#             event=mock_chat_event,
#             name="TestSubAgent",
#             display_name="Test Sub Agent",
#             response_watcher=mock_response_watcher,
#         )

#         # Mock the message step logger
#         mock_message_log = Mock()
#         tool._message_step_logger = Mock()
#         tool._message_step_logger.create_or_update_message_log = Mock(
#             return_value=mock_message_log
#         )

#         tool_call = LanguageModelFunction(
#             id="call_123",
#             name="TestSubAgent",
#             arguments={"user_message": "test message"},
#         )

#         mock_response = {
#             "text": "Sub agent response",
#             "assessment": None,
#             "chatId": "new_chat_id",
#             "references": None,
#         }

#         with (
#             patch.object(
#                 FeatureFlags,
#                 "is_new_answers_ui_enabled",
#                 return_value=True,
#             ),
#             patch(
#                 "unique_toolkit.agentic.tools.a2a.tool.service.send_message_and_wait_for_completion",
#                 new_callable=AsyncMock,
#                 return_value=mock_response,
#             ),
#             patch.object(
#                 tool, "_get_chat_id", new_callable=AsyncMock, return_value=None
#             ),
#             patch.object(
#                 tool, "_save_chat_id", new_callable=AsyncMock, return_value=None
#             ),
#         ):
#             # Act
#             await tool.run(tool_call)

#             # Assert - message log should have been updated with COMPLETED status
#             calls = (
#                 tool._message_step_logger.create_or_update_message_log.call_args_list
#             )
#             assert len(calls) >= 2

#             # Last call should be COMPLETED status
#             last_call = calls[-1]
#             assert last_call.kwargs["status"] == MessageLogStatus.COMPLETED

#     @pytest.mark.ai
#     @pytest.mark.asyncio
#     async def test_run__skips_progress_on_timeout__when_new_ui_enabled_AI(
#         self,
#         mock_sub_agent_config: SubAgentToolConfig,
#         mock_chat_event: ChatEvent,
#     ) -> None:
#         """
#         Purpose: Verify run() skips progress notifications on timeout when new UI is enabled.
#         Why this matters: Error states should also respect the feature flag.
#         Setup summary: Mock SDK to raise TimeoutError, verify no progress notifications were sent.
#         """
#         # Arrange
#         mock_progress_reporter = Mock(spec=ToolProgressReporter)
#         mock_progress_reporter.notify_from_tool_call = AsyncMock()

#         tool = SubAgentTool(
#             configuration=mock_sub_agent_config,
#             event=mock_chat_event,
#             tool_progress_reporter=mock_progress_reporter,
#             name="TestSubAgent",
#             display_name="Test Sub Agent",
#         )

#         # Mock the message step logger
#         mock_message_log = Mock()
#         tool._message_step_logger = Mock()
#         tool._message_step_logger.create_or_update_message_log = Mock(
#             return_value=mock_message_log
#         )

#         tool_call = LanguageModelFunction(
#             id="call_123",
#             name="TestSubAgent",
#             arguments={"user_message": "test message"},
#         )

#         with (
#             patch.object(
#                 FeatureFlags,
#                 "is_new_answers_ui_enabled",
#                 return_value=True,
#             ),
#             patch(
#                 "unique_toolkit.agentic.tools.a2a.tool.service.send_message_and_wait_for_completion",
#                 new_callable=AsyncMock,
#                 side_effect=TimeoutError("Timeout"),
#             ),
#             patch.object(
#                 tool, "_get_chat_id", new_callable=AsyncMock, return_value=None
#             ),
#             pytest.raises(TimeoutError),
#         ):
#             # Act
#             await tool.run(tool_call)

#         # Assert - progress reporter should NOT be called even on error
#         mock_progress_reporter.notify_from_tool_call.assert_not_called()

#     @pytest.mark.ai
#     @pytest.mark.asyncio
#     async def test_run__updates_message_log_to_failed__on_timeout_AI(
#         self,
#         mock_sub_agent_config: SubAgentToolConfig,
#         mock_chat_event: ChatEvent,
#     ) -> None:
#         """
#         Purpose: Verify run() updates message log to FAILED on timeout.
#         Why this matters: Message log should reflect the error state.
#         Setup summary: Mock SDK to raise TimeoutError, verify message log is updated to FAILED.
#         """
#         # Arrange
#         tool = SubAgentTool(
#             configuration=mock_sub_agent_config,
#             event=mock_chat_event,
#             name="TestSubAgent",
#             display_name="Test Sub Agent",
#         )

#         # Mock the message step logger
#         mock_message_log = Mock()
#         tool._message_step_logger = Mock()
#         tool._message_step_logger.create_or_update_message_log = Mock(
#             return_value=mock_message_log
#         )

#         tool_call = LanguageModelFunction(
#             id="call_123",
#             name="TestSubAgent",
#             arguments={"user_message": "test message"},
#         )

#         with (
#             patch.object(
#                 FeatureFlags,
#                 "is_new_answers_ui_enabled",
#                 return_value=True,
#             ),
#             patch(
#                 "unique_toolkit.agentic.tools.a2a.tool.service.send_message_and_wait_for_completion",
#                 new_callable=AsyncMock,
#                 side_effect=TimeoutError("Timeout"),
#             ),
#             patch.object(
#                 tool, "_get_chat_id", new_callable=AsyncMock, return_value=None
#             ),
#             pytest.raises(TimeoutError),
#         ):
#             # Act
#             await tool.run(tool_call)

#         # Assert - message log should have been updated with FAILED status
#         calls = tool._message_step_logger.create_or_update_message_log.call_args_list
#         assert len(calls) >= 1

#         # Last call should be FAILED status
#         last_call = calls[-1]
#         assert last_call.kwargs["status"] == MessageLogStatus.FAILED


# class TestSubAgentToolEvaluation:
#     """Test suite for evaluation-related methods."""

#     @pytest.mark.ai
#     def test_evaluation_check_list__returns_empty_list__when_no_assessment_AI(
#         self,
#         sub_agent_tool: SubAgentTool,
#     ) -> None:
#         """
#         Purpose: Verify evaluation_check_list returns empty list when no assessment ran.
#         Why this matters: Evaluations should only run when sub-agents return assessments.
#         Setup summary: Call method on tool without assessment, verify empty list.
#         """
#         # Act
#         check_list = sub_agent_tool.evaluation_check_list()

#         # Assert
#         assert check_list == []

#     @pytest.mark.ai
#     def test_get_evaluation_checks_based_on_tool_response__returns_empty_list__AI(
#         self,
#         sub_agent_tool: SubAgentTool,
#     ) -> None:
#         """
#         Purpose: Verify evaluation checks based on response returns empty list.
#         Why this matters: SubAgentTool doesn't have response-based evaluation.
#         Setup summary: Create mock response, call method, verify empty list.
#         """
#         # Arrange
#         mock_response = ToolCallResponse(
#             id="test_id",
#             name="TestSubAgent",
#             content="test content",
#         )

#         # Act
#         checks = sub_agent_tool.get_evaluation_checks_based_on_tool_response(
#             mock_response
#         )

#         # Assert
#         assert checks == []


# class TestSubAgentToolStaticMethods:
#     """Test suite for static helper methods."""

#     @pytest.mark.ai
#     def test_get_sub_agent_reference_format__returns_correct_format__AI(self) -> None:
#         """
#         Purpose: Verify reference format is correctly generated.
#         Why this matters: References must follow a specific format for parsing.
#         Setup summary: Call static method with test data, verify format.
#         """
#         # Act
#         result = SubAgentTool.get_sub_agent_reference_format(
#             name="TestAgent", sequence_number=1, reference_number=42
#         )

#         # Assert
#         assert result == "<sup><name>TestAgent 1</name>42</sup>"

#     @pytest.mark.ai
#     def test_get_sub_agent_reference_re__returns_correct_pattern__AI(self) -> None:
#         """
#         Purpose: Verify reference regex pattern is correctly generated.
#         Why this matters: Pattern must match the reference format.
#         Setup summary: Call static method with test data, verify pattern matches expected format.
#         """
#         # Arrange
#         import re

#         pattern = SubAgentTool.get_sub_agent_reference_re(
#             name="TestAgent", sequence_number=1, reference_number=42
#         )

#         # Act
#         test_text = "<sup><name>TestAgent 1</name>42</sup>"
#         match = re.search(pattern, test_text)

#         # Assert
#         assert match is not None
#         assert match.group(0) == test_text
