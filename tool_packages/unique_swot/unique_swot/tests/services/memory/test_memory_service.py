"""Tests for the SwotMemoryService."""

from unittest.mock import Mock

from pydantic import BaseModel

from unique_swot.services.memory.base import Memory, SwotMemoryService


class TestModel(BaseModel):
    """Test model for memory service."""

    value: str
    count: int


def test_memory_service_get_returns_none_when_no_memory():
    """Test that get returns None when no memory exists."""
    kb_service = Mock()
    stm_service = Mock()
    stm_service.find_latest_memory.return_value = None

    service = SwotMemoryService(
        short_term_memory_service=stm_service,
        knowledge_base_service=kb_service,
        cache_scope_id="test_scope",
    )

    result = service.get(TestModel)

    assert result is None


def test_memory_service_get_retrieves_from_kb():
    """Test that get retrieves content from knowledge base."""
    kb_service = Mock()
    kb_service.download_content_to_bytes.return_value = (
        b'{"value": "test", "count": 42}'
    )

    stm_service = Mock()
    memory_data = {"id": "content_123", "file_name": "TestModel_abc.json"}
    stm_service.find_latest_memory.return_value = Mock(data=memory_data)

    service = SwotMemoryService(
        short_term_memory_service=stm_service,
        knowledge_base_service=kb_service,
        cache_scope_id="test_scope",
    )

    result = service.get(TestModel)

    assert result is not None
    assert result.value == "test"
    assert result.count == 42
    kb_service.download_content_to_bytes.assert_called_once_with(
        content_id="content_123"
    )


def test_memory_service_get_handles_kb_error():
    """Test that get handles knowledge base errors gracefully."""
    kb_service = Mock()
    kb_service.download_content_to_bytes.side_effect = Exception("KB error")

    stm_service = Mock()
    memory_data = {"id": "content_123", "file_name": "TestModel_abc.json"}
    stm_service.find_latest_memory.return_value = Mock(data=memory_data)

    service = SwotMemoryService(
        short_term_memory_service=stm_service,
        knowledge_base_service=kb_service,
        cache_scope_id="test_scope",
    )

    result = service.get(TestModel)

    assert result is None


def test_memory_service_set_creates_new_memory():
    """Test that set creates new memory when none exists."""
    kb_service = Mock()
    kb_service.upload_content_from_bytes.return_value = Mock(id="new_content_123")

    stm_service = Mock()
    stm_service.find_latest_memory.return_value = None

    service = SwotMemoryService(
        short_term_memory_service=stm_service,
        knowledge_base_service=kb_service,
        cache_scope_id="test_scope",
    )

    model = TestModel(value="test", count=42)
    service.set(model)

    # Verify upload was called
    kb_service.upload_content_from_bytes.assert_called_once()
    call_kwargs = kb_service.upload_content_from_bytes.call_args.kwargs
    assert call_kwargs["scope_id"] == "test_scope"
    assert call_kwargs["skip_ingestion"] is True

    # Verify short-term memory was created
    stm_service.create_memory.assert_called_once()


def test_memory_service_set_updates_existing_memory():
    """Test that set updates existing memory."""
    kb_service = Mock()
    kb_service.upload_content_from_bytes.return_value = Mock(id="updated_content_123")

    stm_service = Mock()
    memory_data = {"id": "old_content_123", "file_name": "TestModel_existing.json"}
    stm_service.find_latest_memory.return_value = Mock(data=memory_data)

    service = SwotMemoryService(
        short_term_memory_service=stm_service,
        knowledge_base_service=kb_service,
        cache_scope_id="test_scope",
    )

    model = TestModel(value="updated", count=100)
    service.set(model)

    # Verify upload was called with existing file name
    call_kwargs = kb_service.upload_content_from_bytes.call_args.kwargs
    assert call_kwargs["content_name"] == "TestModel_existing.json"


def test_memory_service_set_requires_cache_scope_id():
    """Test that set raises error when cache_scope_id is not set."""
    kb_service = Mock()
    stm_service = Mock()
    stm_service.find_latest_memory.return_value = None

    service = SwotMemoryService(
        short_term_memory_service=stm_service,
        knowledge_base_service=kb_service,
        cache_scope_id="",  # Empty scope ID
    )

    model = TestModel(value="test", count=42)
    service.set(model)

    # Should not upload without scope ID
    kb_service.upload_content_from_bytes.assert_not_called()


def test_memory_service_set_handles_upload_error():
    """Test that set handles upload errors gracefully."""
    kb_service = Mock()
    kb_service.upload_content_from_bytes.side_effect = Exception("Upload error")

    stm_service = Mock()
    stm_service.find_latest_memory.return_value = None

    service = SwotMemoryService(
        short_term_memory_service=stm_service,
        knowledge_base_service=kb_service,
        cache_scope_id="test_scope",
    )

    model = TestModel(value="test", count=42)
    # Should not raise exception
    service.set(model)


def test_memory_service_uses_model_name_as_key():
    """Test that memory service uses model class name as key."""
    kb_service = Mock()
    kb_service.upload_content_from_bytes.return_value = Mock(id="content_123")

    stm_service = Mock()
    stm_service.find_latest_memory.return_value = None

    service = SwotMemoryService(
        short_term_memory_service=stm_service,
        knowledge_base_service=kb_service,
        cache_scope_id="test_scope",
    )

    model = TestModel(value="test", count=42)
    service.set(model)

    # Verify key is class name
    stm_service.create_memory.assert_called_once()
    call_args = stm_service.create_memory.call_args
    assert call_args[0][0] == "TestModel"


def test_memory_service_serializes_json_correctly():
    """Test that memory service serializes models to JSON correctly."""
    kb_service = Mock()
    kb_service.upload_content_from_bytes.return_value = Mock(id="content_123")

    stm_service = Mock()
    stm_service.find_latest_memory.return_value = None

    service = SwotMemoryService(
        short_term_memory_service=stm_service,
        knowledge_base_service=kb_service,
        cache_scope_id="test_scope",
    )

    model = TestModel(value="test", count=42)
    service.set(model)

    # Verify JSON serialization
    call_kwargs = kb_service.upload_content_from_bytes.call_args.kwargs
    content = call_kwargs["content"]
    assert b'"value": "test"' in content
    assert b'"count": 42' in content


def test_memory_model_validation():
    """Test Memory model validation."""
    memory = Memory(id="content_123", file_name="test.json")

    assert memory.id == "content_123"
    assert memory.file_name == "test.json"


def test_memory_service_find_latest_memory_error_handling():
    """Test that find_latest_memory errors are handled."""
    kb_service = Mock()
    stm_service = Mock()
    stm_service.find_latest_memory.side_effect = Exception("STM error")

    service = SwotMemoryService(
        short_term_memory_service=stm_service,
        knowledge_base_service=kb_service,
        cache_scope_id="test_scope",
    )

    result = service.get(TestModel)

    # Should return None on error
    assert result is None


def test_memory_service_mime_type_is_text_plain():
    """Test that uploaded content has text/plain mime type."""
    kb_service = Mock()
    kb_service.upload_content_from_bytes.return_value = Mock(id="content_123")

    stm_service = Mock()
    stm_service.find_latest_memory.return_value = None

    service = SwotMemoryService(
        short_term_memory_service=stm_service,
        knowledge_base_service=kb_service,
        cache_scope_id="test_scope",
    )

    model = TestModel(value="test", count=42)
    service.set(model)

    call_kwargs = kb_service.upload_content_from_bytes.call_args.kwargs
    assert call_kwargs["mime_type"] == "text/plain"
