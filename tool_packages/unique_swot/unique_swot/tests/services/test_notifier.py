# """Tests for notification services."""

# from unittest.mock import Mock

# import pytest
# from unique_toolkit.chat.schemas import MessageLogStatus

# from unique_swot.services.notifier import (
#     LoggerNotifier,
#     Notifier,
#     ProgressNotifier,
#     StepRegistry,
#     _calculate_percentage_completed,
# )


# class TestStepRegistry:
#     """Test cases for StepRegistry class."""

#     def test_step_registry_creation(self):
#         """Test creating a StepRegistry."""
#         registry = StepRegistry(
#             message_log_id="log_123",
#             status=MessageLogStatus.RUNNING,
#             details="Processing step 1",
#         )

#         assert registry.message_log_id == "log_123"
#         assert registry.status == MessageLogStatus.RUNNING
#         assert registry.details == "Processing step 1"


# class TestCalculatePercentageCompleted:
#     """Test cases for _calculate_percentage_completed function."""

#     def test_calculate_percentage_first_step(self):
#         """Test calculating percentage for first step."""
#         result = _calculate_percentage_completed(0, 10)
#         assert result == 10

#     def test_calculate_percentage_middle_step(self):
#         """Test calculating percentage for middle step."""
#         result = _calculate_percentage_completed(4, 10)
#         assert result == 50

#     def test_calculate_percentage_last_step(self):
#         """Test calculating percentage for last step."""
#         result = _calculate_percentage_completed(9, 10)
#         assert result == 100

#     def test_calculate_percentage_single_step(self):
#         """Test calculating percentage for single step."""
#         result = _calculate_percentage_completed(0, 1)
#         assert result == 100

#     def test_calculate_percentage_rounding(self):
#         """Test that percentage is rounded to integer."""
#         result = _calculate_percentage_completed(1, 3)
#         assert isinstance(result, int)
#         assert result == 66  # (2/3) * 100 = 66.66... -> 66


# class TestNotifier:
#     """Test cases for Notifier abstract base class."""

#     def test_notifier_is_abstract(self):
#         """Test that Notifier cannot be instantiated directly."""
#         with pytest.raises(TypeError):
#             Notifier()

#     def test_notifier_requires_notify_implementation(self):
#         """Test that subclasses must implement notify method."""

#         class IncompleteNotifier(Notifier):
#             pass

#         with pytest.raises(TypeError):
#             IncompleteNotifier()


# class TestLoggerNotifier:
#     """Test cases for LoggerNotifier class."""

#     def test_logger_notifier_initialization(self):
#         """Test LoggerNotifier initialization."""
#         notifier = LoggerNotifier()
#         assert isinstance(notifier, Notifier)

#     def test_logger_notifier_notify(self, caplog):
#         """Test LoggerNotifier notify method."""
#         notifier = LoggerNotifier()

#         notifier.notify(step_name="Test Step", progress=0.5)

#         # Check that a log message was created
#         assert "Test Step" in caplog.text
#         assert "0.5" in caplog.text

#     def test_logger_notifier_notify_multiple_times(self, caplog):
#         """Test LoggerNotifier with multiple notifications."""
#         notifier = LoggerNotifier()

#         notifier.notify(step_name="Step 1", progress=0.25)
#         notifier.notify(step_name="Step 2", progress=0.75)

#         assert "Step 1" in caplog.text
#         assert "Step 2" in caplog.text
#         assert "0.25" in caplog.text
#         assert "0.75" in caplog.text

#     def test_logger_notifier_notify_complete(self, caplog):
#         """Test LoggerNotifier with complete progress."""
#         notifier = LoggerNotifier()

#         notifier.notify(step_name="Final Step", progress=1.0)

#         assert "Final Step" in caplog.text
#         assert "1.0" in caplog.text


# class TestProgressNotifier:
#     """Test cases for ProgressNotifier class."""

#     @pytest.fixture
#     def mock_chat_service(self):
#         """Create a mock chat service."""
#         service = Mock()
#         service._assistant_message_id = "test_message_id"
#         service.create_message_execution.return_value = None
#         service.create_message_log.return_value = Mock(message_log_id="log_123")
#         service.update_message_execution.return_value = None
#         return service

#     def test_progress_notifier_initialization(self, mock_chat_service):
#         """Test ProgressNotifier initialization."""
#         notifier = ProgressNotifier(
#             chat_service=mock_chat_service,
#             message_id="msg_123",
#             total_steps=10,
#         )

#         assert notifier._total_steps == 10
#         assert notifier._processed_steps == 0
#         mock_chat_service.create_message_execution.assert_called_once()

#     def test_progress_notifier_progress_percentage_property(self, mock_chat_service):
#         """Test ProgressNotifier progress_percentage property."""
#         notifier = ProgressNotifier(
#             chat_service=mock_chat_service,
#             message_id="msg_123",
#             total_steps=10,
#         )

#         # Initial state
#         assert notifier.progress_precentage == 10  # (0+1)/10 * 100

#         # After processing steps
#         notifier._processed_steps = 4
#         assert notifier.progress_precentage == 50  # (4+1)/10 * 100

#         notifier._processed_steps = 9
#         assert notifier.progress_precentage == 100  # (9+1)/10 * 100

#     def test_progress_notifier_execution_registry(self, mock_chat_service):
#         """Test ProgressNotifier has execution registry."""
#         notifier = ProgressNotifier(
#             chat_service=mock_chat_service,
#             message_id="msg_123",
#             total_steps=5,
#         )

#         assert hasattr(notifier, "_execution_registery")
#         assert isinstance(notifier._execution_registery, dict)
#         assert len(notifier._execution_registery) == 0

#     def test_progress_notifier_with_single_step(self, mock_chat_service):
#         """Test ProgressNotifier with single step."""
#         notifier = ProgressNotifier(
#             chat_service=mock_chat_service,
#             message_id="msg_123",
#             total_steps=1,
#         )

#         assert notifier.progress_precentage == 100

#     def test_progress_notifier_with_many_steps(self, mock_chat_service):
#         """Test ProgressNotifier with many steps."""
#         notifier = ProgressNotifier(
#             chat_service=mock_chat_service,
#             message_id="msg_123",
#             total_steps=100,
#         )

#         notifier._processed_steps = 50
#         assert notifier.progress_precentage == 51  # (50+1)/100 * 100
