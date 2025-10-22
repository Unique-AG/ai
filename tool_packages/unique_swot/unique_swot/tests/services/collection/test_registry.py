"""Tests for content chunk registry."""

from unittest.mock import Mock

import pytest
from unique_toolkit.content.schemas import ContentChunk

from unique_swot.services.collection.registry import (
    ContentChunkRegistry,
    RegistryStore,
)


class TestRegistryStore:
    """Test cases for RegistryStore class."""

    def test_registry_store_initialization(self):
        """Test RegistryStore initialization with default values."""
        store = RegistryStore()

        assert isinstance(store.items, dict)
        assert len(store.items) == 0

    def test_registry_store_with_items(self, sample_content_chunk):
        """Test RegistryStore with items."""
        store = RegistryStore(items={"chunk_1": sample_content_chunk})

        assert len(store.items) == 1
        assert "chunk_1" in store.items


class TestContentChunkRegistry:
    """Test cases for ContentChunkRegistry class."""

    @pytest.fixture
    def mock_memory_service(self):
        """Create a mock memory service."""
        service = Mock()
        service.get.return_value = None
        service.set.return_value = None
        return service

    @pytest.fixture
    def registry(self, mock_memory_service):
        """Create a ContentChunkRegistry instance."""
        return ContentChunkRegistry(memory_service=mock_memory_service)

    def test_registry_initialization_from_scratch(self, mock_memory_service):
        """Test registry initialization when no store exists."""
        mock_memory_service.get.return_value = None

        registry = ContentChunkRegistry(memory_service=mock_memory_service)

        assert isinstance(registry.store, RegistryStore)
        assert len(registry.store.items) == 0

    def test_registry_initialization_from_existing_store(
        self, mock_memory_service, sample_content_chunk
    ):
        """Test registry initialization from existing store."""
        existing_store = RegistryStore(items={"chunk_1": sample_content_chunk})
        mock_memory_service.get.return_value = existing_store

        registry = ContentChunkRegistry(memory_service=mock_memory_service)

        assert len(registry.store.items) == 1
        assert "chunk_1" in registry.store.items

    def test_registry_add_item(self, registry, sample_content_chunk):
        """Test adding an item to the registry."""
        chunk_id = registry.add(sample_content_chunk)

        assert chunk_id.startswith("chunk_")
        assert chunk_id in registry.store.items
        assert registry.store.items[chunk_id] == sample_content_chunk

    def test_registry_add_multiple_items(self, registry, sample_content_chunk):
        """Test adding multiple items to the registry."""
        chunk1 = ContentChunk(
            id="content_1",
            chunk_id="chunk_1",
            title="Doc 1",
            key="doc1.pdf",
            text="Content 1",
        )
        chunk2 = ContentChunk(
            id="content_2",
            chunk_id="chunk_2",
            title="Doc 2",
            key="doc2.pdf",
            text="Content 2",
        )

        id1 = registry.add(chunk1)
        id2 = registry.add(chunk2)

        assert id1 != id2
        assert len(registry.store.items) == 2

    def test_registry_retrieve_existing_item(self, registry, sample_content_chunk):
        """Test retrieving an existing item from the registry."""
        chunk_id = registry.add(sample_content_chunk)

        retrieved = registry.retrieve(chunk_id)

        assert retrieved == sample_content_chunk

    def test_registry_retrieve_non_existing_item(self, registry):
        """Test retrieving a non-existing item returns None."""
        retrieved = registry.retrieve("chunk_nonexistent")

        assert retrieved is None

    def test_registry_save(self, registry, mock_memory_service, sample_content_chunk):
        """Test saving the registry."""
        registry.add(sample_content_chunk)
        registry.save()

        mock_memory_service.set.assert_called_once_with(registry.store)

    def test_registry_generate_unique_id(self, registry):
        """Test that generated IDs are unique."""
        ids = set()
        for _ in range(100):
            # Create a temporary chunk
            chunk = ContentChunk(
                id=f"content_{_}",
                chunk_id=f"chunk_{_}",
                title="Test",
                key="test.pdf",
                text="Content",
            )
            chunk_id = registry.add(chunk)
            ids.add(chunk_id)

        # All IDs should be unique
        assert len(ids) == 100

    def test_registry_id_format(self, registry, sample_content_chunk):
        """Test that generated IDs have correct format."""
        chunk_id = registry.add(sample_content_chunk)

        assert chunk_id.startswith("chunk_")
        # The hex part should be 8 characters
        assert len(chunk_id) == len("chunk_") + 8

    def test_registry_store_property(self, registry):
        """Test accessing the store property."""
        store = registry.store

        assert isinstance(store, RegistryStore)
        assert store == registry._store

    def test_registry_multiple_adds_and_retrieves(self, registry):
        """Test multiple add and retrieve operations."""
        chunks = []
        ids = []

        for i in range(5):
            chunk = ContentChunk(
                id=f"content_{i}",
                chunk_id=f"chunk_{i}",
                title=f"Doc {i}",
                key=f"doc{i}.pdf",
                text=f"Content {i}",
            )
            chunks.append(chunk)
            ids.append(registry.add(chunk))

        # Verify all chunks can be retrieved
        for i, chunk_id in enumerate(ids):
            retrieved = registry.retrieve(chunk_id)
            assert retrieved == chunks[i]
