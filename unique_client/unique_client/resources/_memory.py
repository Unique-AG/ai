from typing import Any

from unique_sdk.api_resources._short_term_memory import ShortTermMemory

from .._base import BaseManager, DomainObject


class MemoryObject(DomainObject):
    """A short-term memory entry."""


class MemoryManager(BaseManager):
    """Store and retrieve short-term memory for a chat session."""

    async def create(self, **params: Any) -> MemoryObject:
        result = await ShortTermMemory.create_async(
            self._user_id, self._company_id, **params
        )
        return MemoryObject(self._user_id, self._company_id, result)

    async def find_latest(self, **params: Any) -> MemoryObject:
        result = await ShortTermMemory.find_latest_async(
            self._user_id, self._company_id, **params
        )
        return MemoryObject(self._user_id, self._company_id, result)
