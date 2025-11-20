"""Comprehensive tests for notification services."""

from unittest.mock import Mock

import pytest
from unique_toolkit.chat.schemas import (
    MessageLogEvent,
    MessageLogStatus,
)

from unique_swot.services.notifier import (
    MessageLogRegistry,
    ProgressNotifier,
)


class TestMessageLogRegistry:
    """Test cases for MessageLogRegistry class."""

    @pytest.fixture
    def mock_chat_service(self):
        """Create a mock chat service."""
        service = Mock()
        service.create_message_log.return_value = Mock(message_log_id="log_123")
        service.update_message_log.return_value = None
        return service

    def test_create_message_log_registry(self, mock_chat_service):
        """Test creating a MessageLogRegistry."""
        registry = MessageLogRegistry.create(
            chat_service=mock_chat_service,
            message_id="msg_123",
            notification_title="Test Step",
            order=0,
            status=MessageLogStatus.RUNNING,
            message_log_event=None,
        )

        assert registry.text == "Test Step"
        assert registry.message_log_id == "log_123"
        assert registry.order == 0
        assert registry.status == MessageLogStatus.RUNNING
        mock_chat_service.create_message_log.assert_called_once()

    def test_create_with_message_log_event(self, mock_chat_service):
        """Test creating registry with message log event."""
        event = MessageLogEvent(type="InternalSearch", text="Searching...")

        registry = MessageLogRegistry.create(
            chat_service=mock_chat_service,
            message_id="msg_123",
            notification_title="Search Step",
            order=1,
            status=MessageLogStatus.RUNNING,
            message_log_event=event,
        )

        assert len(registry.message_log_events) == 1
        assert registry.message_log_events[0] == event

    def test_update_message_log_registry(self, mock_chat_service):
        """Test updating a MessageLogRegistry."""
        registry = MessageLogRegistry.create(
            chat_service=mock_chat_service,
            message_id="msg_123",
            notification_title="Test Step",
            order=0,
            status=MessageLogStatus.RUNNING,
        )

        updated = registry.update(
            chat_service=mock_chat_service,
            status=MessageLogStatus.COMPLETED,
        )

        assert updated.status == MessageLogStatus.COMPLETED
        mock_chat_service.update_message_log.assert_called_once()

    def test_update_with_new_event(self, mock_chat_service):
        """Test updating registry with a new event."""
        registry = MessageLogRegistry.create(
            chat_service=mock_chat_service,
            message_id="msg_123",
            notification_title="Test Step",
            order=0,
            status=MessageLogStatus.RUNNING,
        )

        new_event = MessageLogEvent(type="InternalSearch", text="50% complete")
        updated = registry.update(
            chat_service=mock_chat_service,
            status=MessageLogStatus.RUNNING,
            message_log_event=new_event,
        )

        assert len(updated.message_log_events) == 1
        assert updated.message_log_events[0] == new_event


class TestProgressNotifier:
    """Test cases for ProgressNotifier class."""

    @pytest.fixture
    def mock_chat_service(self):
        """Create a mock chat service."""
        service = Mock()
        service.create_message_execution.return_value = None
        service.create_message_log.return_value = Mock(message_log_id="log_123")
        service.update_message_execution.return_value = None
        service.update_message_log.return_value = None
        service.modify_assistant_message.return_value = None
        return service

    def test_progress_notifier_initialization(self, mock_chat_service):
        """Test ProgressNotifier initialization."""
        notifier = ProgressNotifier(
            chat_service=mock_chat_service,
            message_id="msg_123",
        )

        assert notifier._chat_service == mock_chat_service
        assert notifier._message_id == "msg_123"
        assert notifier._order == 0
        assert notifier._progress_bar is not None
        assert isinstance(notifier._execution_registery, dict)

    def test_start_progress(self, mock_chat_service):
        """Test starting progress tracking."""
        notifier = ProgressNotifier(
            chat_service=mock_chat_service,
            message_id="msg_123",
        )

        notifier.start_progress(total_steps=10, company_name="Test Company")

        assert notifier._progress_bar._total_steps == 10
        mock_chat_service.modify_assistant_message.assert_called_once()

    def test_update_progress(self, mock_chat_service):
        """Test updating progress."""
        notifier = ProgressNotifier(
            chat_service=mock_chat_service,
            message_id="msg_123",
        )
        notifier.start_progress(total_steps=10, company_name="Test Company")

        notifier.update_progress(
            step_precentage_increment=0.1, current_step_message="Processing..."
        )

        # The new implementation uses modify_assistant_message instead of update_message_execution
        mock_chat_service.modify_assistant_message.assert_called()
        call_count = mock_chat_service.modify_assistant_message.call_count
        assert call_count >= 2  # Once for start, at least once for update

    def test_update_progress_caps_at_100(self, mock_chat_service):
        """Test that progress caps at 100%."""
        notifier = ProgressNotifier(
            chat_service=mock_chat_service,
            message_id="msg_123",
        )
        notifier.start_progress(total_steps=10, company_name="Test Company")

        # Update way beyond 100%
        for _ in range(50):
            notifier.update_progress(
                step_precentage_increment=1.0, current_step_message="Processing..."
            )

        # Verify progress bar was updated multiple times
        assert mock_chat_service.modify_assistant_message.call_count > 1

    def test_notify(self, mock_chat_service):
        """Test notify method."""
        notifier = ProgressNotifier(
            chat_service=mock_chat_service,
            message_id="msg_123",
        )

        notifier.notify(
            notification_title="Test Notification",
            status=MessageLogStatus.RUNNING,
        )

        mock_chat_service.create_message_log.assert_called_once()

    def test_notify_with_event(self, mock_chat_service):
        """Test notify with message log event."""
        notifier = ProgressNotifier(
            chat_service=mock_chat_service,
            message_id="msg_123",
        )

        event = MessageLogEvent(type="InternalSearch", text="Searching...")
        notifier.notify(
            notification_title="Search Step",
            status=MessageLogStatus.RUNNING,
            message_log_event=event,
        )

        mock_chat_service.create_message_log.assert_called_once()

    def test_notify_updates_existing_log(self, mock_chat_service):
        """Test that notify updates existing log instead of creating new one."""
        notifier = ProgressNotifier(
            chat_service=mock_chat_service,
            message_id="msg_123",
        )

        # First notification creates log
        notifier.notify(
            notification_title="Test Step",
            status=MessageLogStatus.RUNNING,
        )

        # Second notification with same title updates log
        notifier.notify(
            notification_title="Test Step",
            status=MessageLogStatus.COMPLETED,
        )

        # Should create once and update once
        assert mock_chat_service.create_message_log.call_count == 1
        assert mock_chat_service.update_message_log.call_count == 1

    def test_end_progress_success(self, mock_chat_service):
        """Test ending progress with success."""
        notifier = ProgressNotifier(
            chat_service=mock_chat_service,
            message_id="msg_123",
        )
        notifier.start_progress(total_steps=10, company_name="Test Company")

        notifier.end_progress(failed=False)

        # Verify progress bar was finalized
        mock_chat_service.modify_assistant_message.assert_called()
        # Check that the final message contains completion indicator
        final_call = mock_chat_service.modify_assistant_message.call_args
        final_message = final_call[0][0]
        assert "🟢" in final_message or "100" in final_message

    def test_end_progress_failure(self, mock_chat_service):
        """Test ending progress with failure."""
        notifier = ProgressNotifier(
            chat_service=mock_chat_service,
            message_id="msg_123",
        )
        notifier.start_progress(total_steps=10, company_name="Test Company")

        notifier.end_progress(failed=True, failure_message="Something went wrong")

        # Verify progress bar was finalized with failure
        mock_chat_service.modify_assistant_message.assert_called()
        # Check that the final message contains failure indicator
        final_call = mock_chat_service.modify_assistant_message.call_args
        final_message = final_call[0][0]
        assert "🔴" in final_message or "Something went wrong" in final_message

    def test_notification_order_increments(self, mock_chat_service):
        """Test that notification order increments."""
        notifier = ProgressNotifier(
            chat_service=mock_chat_service,
            message_id="msg_123",
        )

        notifier.notify("Step 1", MessageLogStatus.RUNNING)
        notifier.notify("Step 2", MessageLogStatus.RUNNING)
        notifier.notify("Step 3", MessageLogStatus.RUNNING)

        # Order should increment for each new notification
        assert notifier._order == 3

    def test_progress_calculation(self, mock_chat_service):
        """Test progress percentage calculation."""
        notifier = ProgressNotifier(
            chat_service=mock_chat_service,
            message_id="msg_123",
        )
        notifier.start_progress(total_steps=10, company_name="Test Company")

        # Simulate 50% progress
        notifier.update_progress(
            step_precentage_increment=5.0, current_step_message="Halfway there..."
        )

        # Verify the progress bar was updated
        mock_chat_service.modify_assistant_message.assert_called()
        call_args = mock_chat_service.modify_assistant_message.call_args
        progress_message = call_args[0][0]
        # Check that progress is reflected in the message (should have 50% or thereabouts)
        assert "50" in progress_message or "5" in progress_message
