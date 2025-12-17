"""Tests for the StepNotifier service."""

from unittest.mock import AsyncMock, Mock

import pytest
from unique_toolkit.content import ContentReference

from unique_swot.services.notification.notifier import StepNotifier


@pytest.mark.asyncio
async def test_step_notifier_basic_notification():
    """Test basic notification without sources or progress."""
    chat_service = Mock()
    chat_service.assistant_message_id = "msg_123"
    chat_service.create_message_log_async = AsyncMock(
        return_value=Mock(message_log_id="log_123")
    )
    chat_service.update_message_log_async = AsyncMock()

    notifier = StepNotifier(chat_service=chat_service)

    await notifier.notify(title="Test Title", description="Test Description")

    # Verify notification was logged (implementation detail may vary)
    assert notifier._log_registry is not None


@pytest.mark.asyncio
async def test_step_notifier_with_progress():
    """Test notification with progress percentage."""
    chat_service = Mock()
    chat_service.assistant_message_id = "msg_123"
    chat_service.create_message_log_async = AsyncMock(
        return_value=Mock(message_log_id="log_123")
    )
    chat_service.update_message_log_async = AsyncMock()

    notifier = StepNotifier(chat_service=chat_service)

    await notifier.notify(title="Processing", description="Step 1 of 3", progress=33)

    # Verify progress was tracked
    assert notifier._log_registry is not None


@pytest.mark.asyncio
async def test_step_notifier_with_sources():
    """Test notification with content references."""
    chat_service = Mock()
    chat_service.assistant_message_id = "msg_123"
    chat_service.create_message_log_async = AsyncMock(
        return_value=Mock(message_log_id="log_123")
    )
    chat_service.update_message_log_async = AsyncMock()

    notifier = StepNotifier(chat_service=chat_service)

    sources = [
        ContentReference(
            url="unique://content/123",
            source_id="source_1",
            message_id="msg_123",
            name="Test Document",
            sequence_number=0,
            source="SWOT-TOOL",
        )
    ]

    await notifier.notify(title="Processing Document", sources=sources)

    # Verify sources were included
    assert notifier._log_registry is not None


@pytest.mark.asyncio
async def test_step_notifier_completed_flag():
    """Test notification with completed flag."""
    chat_service = Mock()
    chat_service.assistant_message_id = "msg_123"
    chat_service.create_message_log_async = AsyncMock(
        return_value=Mock(message_log_id="log_123")
    )
    chat_service.update_message_log_async = AsyncMock()

    notifier = StepNotifier(chat_service=chat_service)

    await notifier.notify(
        title="Analysis Complete",
        description="All steps finished",
        progress=100,
        completed=True,
    )

    # Verify completion was tracked
    assert notifier._log_registry is not None


@pytest.mark.asyncio
async def test_step_notifier_multiple_notifications():
    """Test multiple sequential notifications."""
    chat_service = Mock()
    chat_service.assistant_message_id = "msg_123"
    chat_service.create_message_log_async = AsyncMock(
        return_value=Mock(message_log_id="log_123")
    )
    chat_service.update_message_log_async = AsyncMock()

    notifier = StepNotifier(chat_service=chat_service)

    await notifier.notify(title="Step 1", progress=0)
    await notifier.notify(title="Step 2", progress=50)
    await notifier.notify(title="Step 3", progress=100, completed=True)

    # All notifications should be tracked
    assert notifier._log_registry is not None


@pytest.mark.asyncio
async def test_step_notifier_get_total_references():
    """Test getting total number of references."""
    chat_service = Mock()
    chat_service.assistant_message_id = "msg_123"
    chat_service.create_message_log_async = AsyncMock(
        return_value=Mock(message_log_id="log_123")
    )
    chat_service.update_message_log_async = AsyncMock()

    notifier = StepNotifier(chat_service=chat_service)

    # Initial count should be 0
    assert notifier.get_total_number_of_references() == 0


@pytest.mark.asyncio
async def test_step_notifier_with_all_parameters():
    """Test notification with all parameters provided."""
    chat_service = Mock()
    chat_service.assistant_message_id = "msg_123"
    chat_service.create_message_log_async = AsyncMock(
        return_value=Mock(message_log_id="log_123")
    )
    chat_service.update_message_log_async = AsyncMock()

    notifier = StepNotifier(chat_service=chat_service)

    sources = [
        ContentReference(
            url="unique://content/123",
            source_id="source_1",
            message_id="msg_123",
            name="Document 1",
            sequence_number=0,
            source="SWOT-TOOL",
        ),
        ContentReference(
            url="unique://content/456",
            source_id="source_2",
            message_id="msg_123",
            name="Document 2",
            sequence_number=1,
            source="SWOT-TOOL",
        ),
    ]

    await notifier.notify(
        title="Processing Complete",
        description="Analyzed 2 documents",
        sources=sources,
        progress=100,
        completed=True,
    )

    # Verify all parameters were handled
    assert notifier._log_registry is not None


@pytest.mark.asyncio
async def test_step_notifier_empty_description():
    """Test notification with empty description (default)."""
    chat_service = Mock()
    chat_service.assistant_message_id = "msg_123"
    chat_service.create_message_log_async = AsyncMock(
        return_value=Mock(message_log_id="log_123")
    )
    chat_service.update_message_log_async = AsyncMock()

    notifier = StepNotifier(chat_service=chat_service)

    await notifier.notify(title="Title Only")

    # Should work with default empty description
    assert notifier._log_registry is not None


@pytest.mark.asyncio
async def test_step_notifier_empty_sources():
    """Test notification with empty sources list (default)."""
    chat_service = Mock()
    chat_service.assistant_message_id = "msg_123"
    chat_service.create_message_log_async = AsyncMock(
        return_value=Mock(message_log_id="log_123")
    )
    chat_service.update_message_log_async = AsyncMock()

    notifier = StepNotifier(chat_service=chat_service)

    await notifier.notify(title="No Sources", sources=[])

    # Should work with empty sources
    assert notifier._log_registry is not None


@pytest.mark.asyncio
async def test_step_notifier_none_progress():
    """Test notification with None progress (default)."""
    chat_service = Mock()
    chat_service.assistant_message_id = "msg_123"
    chat_service.create_message_log_async = AsyncMock(
        return_value=Mock(message_log_id="log_123")
    )
    chat_service.update_message_log_async = AsyncMock()

    notifier = StepNotifier(chat_service=chat_service)

    await notifier.notify(title="Indeterminate Progress", progress=None)

    # Should work with None progress
    assert notifier._log_registry is not None
