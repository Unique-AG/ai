from unittest.mock import Mock

from unique_toolkit.content import ContentChunk

from unique_swot.services.source_management.registry import (
    ContentChunkRegistry,
    RegistryStore,
)


def _make_chunk(chunk_id="test_chunk"):
    """Helper to create test ContentChunk."""
    return ContentChunk(
        id="content_1",
        chunk_id=chunk_id,
        title="Test Doc",
        key="doc.pdf",
        text="Test content",
        start_page=1,
        end_page=1,
        order=0,
    )


def test_register_generates_unique_ids():
    """Test that register() generates unique IDs for chunks."""
    memory_service = Mock()
    memory_service.get.return_value = None
    registry = ContentChunkRegistry(memory_service=memory_service)

    chunk_a = _make_chunk("chunk_a")
    chunk_b = _make_chunk("chunk_b")

    id_a = registry.register(chunk=chunk_a)
    id_b = registry.register(chunk=chunk_b)

    assert id_a.startswith("chunk_")
    assert id_b.startswith("chunk_")
    assert id_a != id_b


def test_register_and_retrieve():
    """Test that registered chunks can be retrieved by ID."""
    memory_service = Mock()
    memory_service.get.return_value = None
    registry = ContentChunkRegistry(memory_service=memory_service)

    chunk = _make_chunk()
    chunk_id = registry.register(chunk=chunk)

    retrieved = registry.retrieve(chunk_id)
    assert retrieved == chunk
    assert retrieved.chunk_id == chunk.chunk_id


def test_retrieve_nonexistent_returns_none():
    """Test that retrieving a non-existent ID returns None."""
    memory_service = Mock()
    memory_service.get.return_value = None
    registry = ContentChunkRegistry(memory_service=memory_service)

    result = registry.retrieve("nonexistent_id")
    assert result is None


def test_save_persists_store_to_memory_service():
    """Test that save() persists the registry store to memory."""
    memory_service = Mock()
    memory_service.get.return_value = None
    registry = ContentChunkRegistry(memory_service=memory_service)

    chunk = _make_chunk()
    registry.register(chunk=chunk)
    registry.save()

    memory_service.set.assert_called_once()
    stored = memory_service.set.call_args.args[0]
    assert isinstance(stored, RegistryStore)
    assert len(stored.items) == 1


def test_registry_initializes_from_existing_store():
    """Test that registry can initialize from an existing store in memory."""
    existing_chunk = _make_chunk()
    existing_store = RegistryStore(items={"chunk_existing": existing_chunk})

    memory_service = Mock()
    memory_service.get.return_value = existing_store

    registry = ContentChunkRegistry(memory_service=memory_service)

    # Should be able to retrieve the existing chunk
    retrieved = registry.retrieve("chunk_existing")
    assert retrieved == existing_chunk


def test_registry_store_property():
    """Test that the store property returns the internal store."""
    memory_service = Mock()
    memory_service.get.return_value = None
    registry = ContentChunkRegistry(memory_service=memory_service)

    store = registry.store
    assert isinstance(store, RegistryStore)
    assert store.items == {}


def test_multiple_registrations_maintain_order():
    """Test that multiple registrations maintain separate entries."""
    memory_service = Mock()
    memory_service.get.return_value = None
    registry = ContentChunkRegistry(memory_service=memory_service)

    chunks = [_make_chunk(f"chunk_{i}") for i in range(5)]
    ids = [registry.register(chunk=chunk) for chunk in chunks]

    # All IDs should be unique
    assert len(set(ids)) == 5

    # All chunks should be retrievable
    for chunk_id, original_chunk in zip(ids, chunks):
        retrieved = registry.retrieve(chunk_id)
        assert retrieved == original_chunk


def test_id_collision_handling():
    """Test that the registry handles ID collisions by retrying."""
    memory_service = Mock()
    memory_service.get.return_value = None
    registry = ContentChunkRegistry(memory_service=memory_service)

    # Register many chunks to increase chance of testing collision logic
    chunks = [_make_chunk(f"chunk_{i}") for i in range(20)]
    ids = [registry.register(chunk=chunk) for chunk in chunks]

    # All IDs should still be unique
    assert len(set(ids)) == 20
