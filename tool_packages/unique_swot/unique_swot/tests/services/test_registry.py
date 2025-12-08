from unittest.mock import Mock

from unique_toolkit.content import ContentChunk

from unique_swot.services.source_management.registry import (
    ContentChunkRegistry,
    RegistryStore,
)


def test_register_and_retrieve_generates_unique_ids():
    memory_service = Mock()
    memory_service.get.return_value = None
    registry = ContentChunkRegistry(memory_service=memory_service)

    chunk_a = Mock(spec=ContentChunk)
    chunk_b = Mock(spec=ContentChunk)

    id_a = registry.register_and_generate_id(chunk_a)
    id_b = registry.register_and_generate_id(chunk_b)

    assert id_a.startswith("chunk_")
    assert id_b.startswith("chunk_")
    assert id_a != id_b
    assert registry.retrieve(id_a) is chunk_a
    assert registry.retrieve(id_b) is chunk_b


def test_save_persists_store_to_memory_service():
    memory_service = Mock()
    memory_service.get.return_value = None
    registry = ContentChunkRegistry(memory_service=memory_service)

    registry.save()

    memory_service.set.assert_called_once()
    stored = memory_service.set.call_args.args[0]
    assert isinstance(stored, RegistryStore)
