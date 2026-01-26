"""Tests for the LogRegistry and MessageLogRegistryItem."""

from unittest.mock import AsyncMock, Mock

import pytest
from unique_toolkit.chat.schemas import MessageLogStatus
from unique_toolkit.content import ContentReference

from unique_swot.services.notification.log_registry import (
    LogRegistry,
    MessageLogRegistryItem,
)


@pytest.fixture
def mock_chat_service():
    """Create a mock chat service for testing."""
    chat_service = Mock()
    chat_service.create_message_log_async = AsyncMock(
        return_value=Mock(message_log_id="log_123")
    )
    chat_service.update_message_log_async = AsyncMock()
    return chat_service


@pytest.fixture
def sample_sources():
    """Create sample content references for testing."""
    return [
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


# MessageLogRegistryItem Tests


@pytest.mark.asyncio
async def test_message_log_registry_item_create_basic(mock_chat_service):
    """Test creating a basic MessageLogRegistryItem."""
    item = await MessageLogRegistryItem.create(
        chat_service=mock_chat_service,
        order=1,
        message_id="msg_123",
        title="Test Title",
        description="Test Description",
    )

    assert item.title == "Test Title"
    assert item.description == ["Test Description"]
    assert item.sources == []
    assert item.message_log_id == "log_123"
    assert item.order == 1
    assert item.progress == 0
    assert item.completed is False

    # Verify chat service was called correctly
    mock_chat_service.create_message_log_async.assert_called_once()
    call_args = mock_chat_service.create_message_log_async.call_args
    assert call_args.kwargs["message_id"] == "msg_123"
    assert call_args.kwargs["order"] == 1
    assert "Test Title" in call_args.kwargs["text"]
    assert call_args.kwargs["status"] == MessageLogStatus.RUNNING


@pytest.mark.asyncio
async def test_message_log_registry_item_create_with_sources(
    mock_chat_service, sample_sources
):
    """Test creating a MessageLogRegistryItem with sources."""
    item = await MessageLogRegistryItem.create(
        chat_service=mock_chat_service,
        order=1,
        message_id="msg_123",
        title="Processing Documents",
        description="Analyzing sources",
        sources=sample_sources,
        progress=50,
    )

    assert item.sources == sample_sources
    assert item.progress == 50
    assert len(item.sources) == 2

    # Verify uncited_references were included
    call_args = mock_chat_service.create_message_log_async.call_args
    assert call_args.kwargs["uncited_references"].data == sample_sources


@pytest.mark.asyncio
async def test_message_log_registry_item_create_completed(mock_chat_service):
    """Test creating a completed MessageLogRegistryItem."""
    item = await MessageLogRegistryItem.create(
        chat_service=mock_chat_service,
        order=1,
        message_id="msg_123",
        title="Task Complete",
        description="All done",
        progress=100,
        completed=True,
    )

    assert item.completed is True
    assert item.progress == 100

    # Verify status is COMPLETED
    call_args = mock_chat_service.create_message_log_async.call_args
    assert call_args.kwargs["status"] == MessageLogStatus.COMPLETED


@pytest.mark.asyncio
async def test_message_log_registry_item_update_basic(mock_chat_service):
    """Test updating a MessageLogRegistryItem."""
    item = await MessageLogRegistryItem.create(
        chat_service=mock_chat_service,
        order=1,
        message_id="msg_123",
        title="Test Title",
        description="Initial description",
        progress=0,
    )

    # Reset mock to track update call
    mock_chat_service.update_message_log_async.reset_mock()

    # Update the item
    updated_item = await item.update(
        chat_service=mock_chat_service,
        description="Updated description",
        sources=[],
        progress=50,
    )

    assert updated_item.description == ["Initial description", "Updated description"]
    assert updated_item.progress == 50
    assert updated_item.completed is False

    # Verify update was called
    mock_chat_service.update_message_log_async.assert_called_once()
    call_args = mock_chat_service.update_message_log_async.call_args
    assert call_args.kwargs["message_log_id"] == "log_123"
    assert call_args.kwargs["status"] == MessageLogStatus.RUNNING


@pytest.mark.asyncio
async def test_message_log_registry_item_update_with_sources(
    mock_chat_service, sample_sources
):
    """Test updating a MessageLogRegistryItem with new sources."""
    item = await MessageLogRegistryItem.create(
        chat_service=mock_chat_service,
        order=1,
        message_id="msg_123",
        title="Test Title",
        description="Initial description",
    )

    mock_chat_service.update_message_log_async.reset_mock()

    # Add sources via update
    new_source = ContentReference(
        url="unique://content/789",
        source_id="source_3",
        message_id="msg_123",
        name="Document 3",
        sequence_number=2,
        source="SWOT-TOOL",
    )

    updated_item = await item.update(
        chat_service=mock_chat_service,
        description="Added sources",
        sources=[new_source],
    )

    assert len(updated_item.sources) == 1
    assert updated_item.sources[0] == new_source

    # Verify uncited_references were updated
    call_args = mock_chat_service.update_message_log_async.call_args
    assert call_args.kwargs["uncited_references"].data == [new_source]


@pytest.mark.asyncio
async def test_message_log_registry_item_update_completed(mock_chat_service):
    """Test updating a MessageLogRegistryItem to completed status."""
    item = await MessageLogRegistryItem.create(
        chat_service=mock_chat_service,
        order=1,
        message_id="msg_123",
        title="Test Title",
        description="Initial description",
        progress=50,
    )

    mock_chat_service.update_message_log_async.reset_mock()

    # Mark as completed
    updated_item = await item.update(
        chat_service=mock_chat_service,
        description="Finished",
        sources=[],
        progress=100,
        completed=True,
    )

    assert updated_item.progress == 100

    # Verify status was set to COMPLETED in the API call
    call_args = mock_chat_service.update_message_log_async.call_args
    assert call_args.kwargs["status"] == MessageLogStatus.COMPLETED


@pytest.mark.asyncio
async def test_message_log_registry_item_update_preserves_progress(mock_chat_service):
    """Test that update preserves progress when progress is None."""
    item = await MessageLogRegistryItem.create(
        chat_service=mock_chat_service,
        order=1,
        message_id="msg_123",
        title="Test Title",
        description="Initial description",
        progress=50,
    )

    mock_chat_service.update_message_log_async.reset_mock()

    # Update without specifying progress
    updated_item = await item.update(
        chat_service=mock_chat_service,
        description="Updated",
        sources=[],
        progress=None,  # Should preserve existing progress
    )

    assert updated_item.progress == 50  # Unchanged


@pytest.mark.asyncio
async def test_message_log_registry_item_multiple_updates(mock_chat_service):
    """Test multiple sequential updates to a MessageLogRegistryItem."""
    item = await MessageLogRegistryItem.create(
        chat_service=mock_chat_service,
        order=1,
        message_id="msg_123",
        title="Test Title",
        description="Step 1",
        progress=0,
    )

    # Multiple updates
    await item.update(
        chat_service=mock_chat_service,
        description="Step 2",
        sources=[],
        progress=25,
    )

    await item.update(
        chat_service=mock_chat_service,
        description="Step 3",
        sources=[],
        progress=50,
    )

    await item.update(
        chat_service=mock_chat_service,
        description="Step 4",
        sources=[],
        progress=75,
    )

    # Should have all descriptions
    assert item.description == ["Step 1", "Step 2", "Step 3", "Step 4"]
    assert item.progress == 75


# LogRegistry Tests


@pytest.mark.asyncio
async def test_log_registry_initialization():
    """Test LogRegistry initialization."""
    registry = LogRegistry()

    assert registry._log_registry == {}
    assert registry._total_number_of_references == 0


@pytest.mark.asyncio
async def test_log_registry_add_new_entry(mock_chat_service):
    """Test adding a new entry to LogRegistry."""
    registry = LogRegistry()

    await registry.add(
        chat_service=mock_chat_service,
        message_id="msg_123",
        title="Test Entry",
        description="Test description",
        progress=25,
    )

    assert "Test Entry" in registry._log_registry
    item = registry._log_registry["Test Entry"]
    assert item.title == "Test Entry"
    assert item.description == ["Test description"]
    assert item.progress == 25
    assert item.order == 99  # First entry gets order 99


@pytest.mark.asyncio
async def test_log_registry_add_updates_existing_entry(mock_chat_service):
    """Test that adding an existing title updates the entry."""
    registry = LogRegistry()

    # Add initial entry
    await registry.add(
        chat_service=mock_chat_service,
        message_id="msg_123",
        title="Test Entry",
        description="Initial description",
        progress=25,
    )

    mock_chat_service.update_message_log_async.reset_mock()

    # Add with same title - should update
    await registry.add(
        chat_service=mock_chat_service,
        message_id="msg_123",
        title="Test Entry",
        description="Updated description",
        progress=50,
    )

    # Should still be only one entry
    assert len(registry._log_registry) == 1
    item = registry._log_registry["Test Entry"]
    assert item.description == ["Initial description", "Updated description"]
    assert item.progress == 50

    # Verify update was called
    mock_chat_service.update_message_log_async.assert_called_once()


@pytest.mark.asyncio
async def test_log_registry_sequence_numbers(mock_chat_service, sample_sources):
    """Test that sequence numbers are assigned correctly."""
    registry = LogRegistry()

    # Add first entry with sources
    await registry.add(
        chat_service=mock_chat_service,
        message_id="msg_123",
        title="Entry 1",
        description="First entry",
        sources=sample_sources[:1],  # 1 source
    )

    assert registry._total_number_of_references == 1
    assert sample_sources[0].sequence_number == 0

    # Add second entry with more sources
    more_sources = [
        ContentReference(
            url="unique://content/789",
            source_id="source_3",
            message_id="msg_123",
            name="Document 3",
            sequence_number=0,
            source="SWOT-TOOL",
        ),
        ContentReference(
            url="unique://content/101",
            source_id="source_4",
            message_id="msg_123",
            name="Document 4",
            sequence_number=0,
            source="SWOT-TOOL",
        ),
    ]

    await registry.add(
        chat_service=mock_chat_service,
        message_id="msg_123",
        title="Entry 2",
        description="Second entry",
        sources=more_sources,
    )

    assert registry._total_number_of_references == 3
    assert more_sources[0].sequence_number == 1  # Continues from previous
    assert more_sources[1].sequence_number == 2


@pytest.mark.asyncio
async def test_log_registry_multiple_entries_order(mock_chat_service):
    """Test that multiple entries get correct order values."""
    registry = LogRegistry()

    # Add three entries
    await registry.add(
        chat_service=mock_chat_service,
        message_id="msg_123",
        title="Entry 1",
        description="First",
    )

    await registry.add(
        chat_service=mock_chat_service,
        message_id="msg_123",
        title="Entry 2",
        description="Second",
    )

    await registry.add(
        chat_service=mock_chat_service,
        message_id="msg_123",
        title="Entry 3",
        description="Third",
    )

    # Check order values
    assert registry._log_registry["Entry 1"].order == 99
    assert registry._log_registry["Entry 2"].order == 100
    assert registry._log_registry["Entry 3"].order == 101


@pytest.mark.asyncio
async def test_log_registry_add_with_completed_flag(mock_chat_service):
    """Test adding a completed entry to LogRegistry."""
    registry = LogRegistry()

    await registry.add(
        chat_service=mock_chat_service,
        message_id="msg_123",
        title="Completed Task",
        description="All done",
        progress=100,
        completed=True,
    )

    item = registry._log_registry["Completed Task"]
    assert item.completed is True
    assert item.progress == 100


@pytest.mark.asyncio
async def test_log_registry_add_without_progress(mock_chat_service):
    """Test adding an entry without progress defaults to 0."""
    registry = LogRegistry()

    await registry.add(
        chat_service=mock_chat_service,
        message_id="msg_123",
        title="No Progress",
        description="Default progress",
        progress=None,
    )

    item = registry._log_registry["No Progress"]
    assert item.progress == 0


@pytest.mark.asyncio
async def test_log_registry_update_preserves_progress(mock_chat_service):
    """Test that updating without progress preserves existing value."""
    registry = LogRegistry()

    # Add with initial progress
    await registry.add(
        chat_service=mock_chat_service,
        message_id="msg_123",
        title="Test Entry",
        description="Initial",
        progress=50,
    )

    # Update without progress
    await registry.add(
        chat_service=mock_chat_service,
        message_id="msg_123",
        title="Test Entry",
        description="Updated",
        progress=None,  # Should preserve 50
    )

    item = registry._log_registry["Test Entry"]
    assert item.progress == 50


@pytest.mark.asyncio
async def test_log_registry_empty_sources(mock_chat_service):
    """Test adding entries with empty sources list."""
    registry = LogRegistry()

    await registry.add(
        chat_service=mock_chat_service,
        message_id="msg_123",
        title="No Sources",
        description="Entry without sources",
        sources=[],
    )

    assert registry._total_number_of_references == 0
    item = registry._log_registry["No Sources"]
    assert item.sources == []


@pytest.mark.asyncio
async def test_log_registry_text_formatting(mock_chat_service):
    """Test that the text formatting includes title, progress, and descriptions."""
    registry = LogRegistry()

    await registry.add(
        chat_service=mock_chat_service,
        message_id="msg_123",
        title="Test Task",
        description="First step",
        progress=33,
    )

    # Check the create call had correct formatting
    call_args = mock_chat_service.create_message_log_async.call_args
    text = call_args.kwargs["text"]
    assert "**Test Task**" in text
    assert "_33%_" in text
    assert "First step" in text

    # Update and check formatting again
    await registry.add(
        chat_service=mock_chat_service,
        message_id="msg_123",
        title="Test Task",
        description="Second step",
        progress=66,
    )

    update_call_args = mock_chat_service.update_message_log_async.call_args
    updated_text = update_call_args.kwargs["text"]
    assert "**Test Task**" in updated_text
    assert "_66%_" in updated_text
    assert "First step" in updated_text
    assert "Second step" in updated_text
