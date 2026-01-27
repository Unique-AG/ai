from unittest.mock import AsyncMock, Mock

import pytest

from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ToolProgressReporter,
    ToolProgressReporterProtocol,
)
from unique_toolkit.chat.schemas import MessageLog, MessageLogStatus
from unique_toolkit.chat.service import ChatService
from unique_toolkit.language_model.schemas import LanguageModelFunction


@pytest.fixture
def chat_service() -> AsyncMock:
    """Provide a mock ChatService for testing."""
    return AsyncMock(spec=ChatService)


@pytest.fixture
def tool_call() -> LanguageModelFunction:
    """Provide a test tool call."""
    return LanguageModelFunction(id="test_id", name="test_tool")


@pytest.fixture
def tool_progress_reporter(chat_service: AsyncMock) -> ToolProgressReporter:
    """Provide a ToolProgressReporter instance for testing."""
    return ToolProgressReporter(chat_service)


@pytest.fixture
def message_step_logger() -> Mock:
    """Create a mock MessageStepLogger."""
    logger = Mock(spec=MessageStepLogger)
    logger.create_or_update_message_log = Mock(
        return_value=MessageLog(
            message_log_id="log_1", order=1, status=MessageLogStatus.RUNNING
        )
    )
    return logger


@pytest.fixture
def mock_reporter_1() -> Mock:
    """Create first mock reporter."""
    reporter = Mock(spec=ToolProgressReporterProtocol)
    reporter.notify_from_tool_call = AsyncMock()
    return reporter


@pytest.fixture
def mock_reporter_2() -> Mock:
    """Create second mock reporter."""
    reporter = Mock(spec=ToolProgressReporterProtocol)
    reporter.notify_from_tool_call = AsyncMock()
    return reporter
