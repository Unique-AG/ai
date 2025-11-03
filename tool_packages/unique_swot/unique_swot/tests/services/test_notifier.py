"""Comprehensive tests for notification services."""

from unittest.mock import Mock

import pytest
from unique_toolkit.chat.schemas import (
    MessageExecutionUpdateStatus,
    MessageLogEvent,
    MessageLogStatus,
)

from unique_swot.services.notifier import (
    MessageLogRegistry,
    ProgressNotifier,
    _calculate_percentage_completed,
)


class TestCalculatePercentageCompleted:
    """Test cases for _calculate_percentage_completed function."""

    def test_calculate_percentage_zero_progress(self):
        """Test calculating percentage with zero current step."""
        result = _calculate_percentage_completed(0, 10)
        assert result == 0

    def test_calculate_percentage_middle_step(self):
        """Test calculating percentage for middle step."""
        result = _calculate_percentage_completed(5, 10)
        assert result == 50

    def test_calculate_percentage_complete(self):
        """Test calculating percentage for completed steps."""
        result = _calculate_percentage_completed(10, 10)
        assert result == 100

    def test_calculate_percentage_single_step(self):
        """Test calculating percentage for single step."""
        result = _calculate_percentage_completed(1, 1)
        assert result == 100

    def test_calculate_percentage_rounding(self):
        """Test that percentage is rounded to integer."""
        result = _calculate_percentage_completed(1, 3)
        assert isinstance(result, int)
        assert result == 33  # (1/3) * 100 = 33.33... -> 33

    def test_calculate_percentage_returns_integer(self):
        """Test that function always returns an integer."""
        result = _calculate_percentage_completed(7, 11)
        assert isinstance(result, int)


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
        assert notifier._step_increment == 0
        assert isinstance(notifier._execution_registery, dict)

    def test_start_progress(self, mock_chat_service):
        """Test starting progress tracking."""
        notifier = ProgressNotifier(
            chat_service=mock_chat_service,
            message_id="msg_123",
        )

        notifier.start_progress(total_steps=10)

        assert notifier._total_steps == 10
        mock_chat_service.create_message_execution.assert_called_once()

    def test_update_progress(self, mock_chat_service):
        """Test updating progress."""
        notifier = ProgressNotifier(
            chat_service=mock_chat_service,
            message_id="msg_123",
        )
        notifier.start_progress(total_steps=10)

        notifier.update_progress(step_precentage_increment=0.1)

        mock_chat_service.update_message_execution.assert_called()
        call_args = mock_chat_service.update_message_execution.call_args
        assert call_args[1]["message_id"] == "msg_123"
        assert "percentage_completed" in call_args[1]

    def test_update_progress_caps_at_100(self, mock_chat_service):
        """Test that progress caps at 100%."""
        notifier = ProgressNotifier(
            chat_service=mock_chat_service,
            message_id="msg_123",
        )
        notifier.start_progress(total_steps=10)

        # Update way beyond 100%
        for _ in range(50):
            notifier.update_progress(step_precentage_increment=1.0)

        # Should be capped at 100
        call_args = mock_chat_service.update_message_execution.call_args
        assert call_args[1]["percentage_completed"] == 100

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
        notifier.start_progress(total_steps=10)

        notifier.end_progress(success=True)

        call_args = mock_chat_service.update_message_execution.call_args
        assert call_args[1]["status"] == MessageExecutionUpdateStatus.COMPLETED
        assert call_args[1]["percentage_completed"] == 100

    def test_end_progress_failure(self, mock_chat_service):
        """Test ending progress with failure."""
        notifier = ProgressNotifier(
            chat_service=mock_chat_service,
            message_id="msg_123",
        )
        notifier.start_progress(total_steps=10)

        notifier.end_progress(success=False)

        call_args = mock_chat_service.update_message_execution.call_args
        assert call_args[1]["status"] == MessageExecutionUpdateStatus.FAILED
        assert call_args[1]["percentage_completed"] == 100

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
        notifier.start_progress(total_steps=10)

        # Simulate 50% progress
        notifier.update_progress(step_precentage_increment=5.0)

        call_args = mock_chat_service.update_message_execution.call_args
        percentage = call_args[1]["percentage_completed"]
        assert 45 <= percentage <= 55  # Allow some rounding variance
