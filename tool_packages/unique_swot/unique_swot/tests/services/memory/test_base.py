"""Tests for SWOT memory service."""

from unittest.mock import Mock

import pytest
from pydantic import BaseModel

from unique_swot.services.memory.base import Memory, SwotMemoryService


class SampleModel(BaseModel):
    """Sample model for testing."""

    data: str
    value: int


class TestMemory:
    """Test cases for Memory class."""

    def test_memory_creation(self):
        """Test creating a Memory instance."""
        memory = Memory(id="mem_123", file_name="test.json")

        assert memory.id == "mem_123"
        assert memory.file_name == "test.json"


class TestSwotMemoryService:
    """Test cases for SwotMemoryService class."""

    @pytest.fixture
    def mock_short_term_memory_service(self):
        """Create a mock short term memory service."""
        service = Mock()
        service.create_memory.return_value = None
        service.find_latest_memory.return_value = None
        return service

    @pytest.fixture
    def mock_knowledge_base_service(self):
        """Create a mock knowledge base service."""
        service = Mock()
        service.upload_content_from_bytes.return_value = Mock(id="content_123")
        service.download_content_to_bytes.return_value = (
            b'{"data": "test", "value": 42}'
        )
        return service

    @pytest.fixture
    def memory_service(
        self, mock_short_term_memory_service, mock_knowledge_base_service
    ):
        """Create a SwotMemoryService instance."""
        return SwotMemoryService(
            short_term_memory_service=mock_short_term_memory_service,
            knowledge_base_service=mock_knowledge_base_service,
            cache_scope_id="test_scope",
        )

    def test_memory_service_initialization(self, memory_service):
        """Test SwotMemoryService initialization."""
        assert memory_service._cache_scope_id == "test_scope"
        assert memory_service._short_term_memory_service is not None
        assert memory_service._knowledge_base_service is not None

    def test_get_no_memory_found(self, memory_service, mock_short_term_memory_service):
        """Test getting memory when no memory exists."""
        mock_short_term_memory_service.find_latest_memory.return_value = None

        result = memory_service.get(SampleModel)

        assert result is None

    def test_get_memory_found(
        self,
        memory_service,
        mock_short_term_memory_service,
        mock_knowledge_base_service,
    ):
        """Test getting memory when it exists."""
        # Mock the short term memory response
        mock_memory_response = Mock()
        mock_memory_response.data = {
            "id": "content_123",
            "file_name": "SampleModel_abc.json",
        }
        mock_short_term_memory_service.find_latest_memory.return_value = (
            mock_memory_response
        )

        result = memory_service.get(SampleModel)

        assert result is not None
        assert isinstance(result, SampleModel)
        assert result.data == "test"
        assert result.value == 42

    def test_get_memory_error_handling(
        self,
        memory_service,
        mock_short_term_memory_service,
    ):
        """Test that get handles errors gracefully."""
        mock_short_term_memory_service.find_latest_memory.side_effect = Exception(
            "Memory error"
        )

        result = memory_service.get(SampleModel)

        assert result is None

    def test_set_new_memory(
        self,
        memory_service,
        mock_short_term_memory_service,
        mock_knowledge_base_service,
    ):
        """Test setting a new memory."""
        mock_short_term_memory_service.find_latest_memory.return_value = None

        sample_data = SampleModel(data="new data", value=100)
        memory_service.set(sample_data)

        # Should upload to knowledge base
        mock_knowledge_base_service.upload_content_from_bytes.assert_called_once()
        # Should create short term memory
        mock_short_term_memory_service.create_memory.assert_called_once()

    def test_set_existing_memory(
        self,
        memory_service,
        mock_short_term_memory_service,
        mock_knowledge_base_service,
    ):
        """Test updating an existing memory."""
        # Mock existing memory
        mock_memory_response = Mock()
        mock_memory_response.data = {
            "id": "old_content_123",
            "file_name": "SampleModel_existing.json",
        }
        mock_short_term_memory_service.find_latest_memory.return_value = (
            mock_memory_response
        )

        sample_data = SampleModel(data="updated data", value=200)
        memory_service.set(sample_data)

        # Should still upload to knowledge base
        mock_knowledge_base_service.upload_content_from_bytes.assert_called_once()
        # Should create new short term memory entry
        mock_short_term_memory_service.create_memory.assert_called_once()

    def test_set_with_correct_scope(
        self,
        memory_service,
        mock_short_term_memory_service,
        mock_knowledge_base_service,
    ):
        """Test that set uses correct scope_id."""
        mock_short_term_memory_service.find_latest_memory.return_value = None

        sample_data = SampleModel(data="test", value=50)
        memory_service.set(sample_data)

        # Check that scope_id was passed correctly
        call_args = mock_knowledge_base_service.upload_content_from_bytes.call_args
        assert call_args.kwargs["scope_id"] == "test_scope"

    def test_set_skip_ingestion(
        self,
        memory_service,
        mock_short_term_memory_service,
        mock_knowledge_base_service,
    ):
        """Test that set skips ingestion when uploading."""
        mock_short_term_memory_service.find_latest_memory.return_value = None

        sample_data = SampleModel(data="test", value=50)
        memory_service.set(sample_data)

        # Check that skip_ingestion=True
        call_args = mock_knowledge_base_service.upload_content_from_bytes.call_args
        assert call_args.kwargs["skip_ingestion"] is True

    def test_find_latest_memory_success(
        self,
        memory_service,
        mock_short_term_memory_service,
    ):
        """Test finding latest memory successfully."""
        mock_memory_response = Mock()
        mock_memory_response.data = {"id": "content_123", "file_name": "test.json"}
        mock_short_term_memory_service.find_latest_memory.return_value = (
            mock_memory_response
        )

        memory = memory_service._find_latest_memory("SampleModel")

        assert memory is not None
        assert memory.id == "content_123"
        assert memory.file_name == "test.json"

    def test_find_latest_memory_error_handling(
        self,
        memory_service,
        mock_short_term_memory_service,
    ):
        """Test that _find_latest_memory handles errors gracefully."""
        mock_short_term_memory_service.find_latest_memory.side_effect = Exception(
            "Error"
        )

        memory = memory_service._find_latest_memory("SampleModel")

        assert memory is None

    def test_memory_key_uses_class_name(
        self,
        memory_service,
        mock_short_term_memory_service,
        mock_knowledge_base_service,
    ):
        """Test that memory key is based on class name."""
        mock_short_term_memory_service.find_latest_memory.return_value = None

        sample_data = SampleModel(data="test", value=10)
        memory_service.set(sample_data)

        # Check that the key used is the class name
        call_args = mock_short_term_memory_service.create_memory.call_args
        assert call_args[0][0] == "SampleModel"

    def test_get_invalid_json(
        self,
        memory_service,
        mock_short_term_memory_service,
        mock_knowledge_base_service,
    ):
        """Test getting memory with invalid JSON data."""
        mock_memory_response = Mock()
        mock_memory_response.data = {"id": "content_123", "file_name": "test.json"}
        mock_short_term_memory_service.find_latest_memory.return_value = (
            mock_memory_response
        )
        mock_knowledge_base_service.download_content_to_bytes.return_value = (
            b"invalid json"
        )

        result = memory_service.get(SampleModel)

        # Should handle the error and return None
        assert result is None
