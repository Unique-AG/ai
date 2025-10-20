from logging import getLogger
from uuid import uuid4

from pydantic import BaseModel, Field
from unique_toolkit.content import ContentChunk

from unique_swot.services.memory import SwotMemoryService

_MAX_RETRIES = 100

_LOGGER = getLogger(__name__)


class RegistryStore(BaseModel):
    items: dict[str, ContentChunk] = Field(default_factory=dict)


class ContentChunkRegistry:
    def __init__(self, memory_service: SwotMemoryService[RegistryStore]):
        self._memory_service = memory_service

        store = self._memory_service.get(RegistryStore)

        if store is not None:
            _LOGGER.info("Initializing collection registry from provided store.")
            self._store = store
        else:
            _LOGGER.info("Initializing a new collection registry from scratch.")
            self._store = RegistryStore(items={})
            
    @property
    def store(self) -> RegistryStore:
        return self._store

    def save(self):
        self._memory_service.set(self._store)

    def add(self, item: ContentChunk) -> str:
        """Add an item and return its unique ID."""
        id = self._generate_unique_id()
        self._store.items[id] = item
        return id

    def retrieve(self, id: str) -> ContentChunk | None:
        """Retrieve an item by its ID."""
        return self._store.items.get(id)

    def _generate_unique_id(self) -> str:
        for _ in range(_MAX_RETRIES):
            id = uuid4().hex[:8]
            if id not in self._store.items:
                return id
            _LOGGER.warning(f"Registry ID collision detected for ID: {id}. Retrying...")
        raise ValueError("Failed to generate a unique ID for the registry")
