from typing import Any

from unique_sdk.api_resources._space import Space

from .._base import BaseManager, DomainObject


class SpaceObject(DomainObject):
    """A Unique AI space (chat room / assistant configuration) with mutation methods."""

    # ------------------------------------------------------------------
    # Space-level operations
    # ------------------------------------------------------------------

    async def update(self, **params: Any) -> "SpaceObject":
        result = await Space.update_space_async(
            self._user_id, self._company_id, self.id, **params
        )
        self._update_raw(result)
        return self

    async def delete(self) -> Any:
        return await Space.delete_space_async(
            self._user_id, self._company_id, self.id
        )

    # ------------------------------------------------------------------
    # Access management
    # ------------------------------------------------------------------

    async def get_access(self) -> Any:
        return await Space.get_space_access_async(
            self._user_id, self._company_id, self.id
        )

    async def add_access(self, **params: Any) -> Any:
        return await Space.add_space_access_async(
            self._user_id, self._company_id, self.id, **params
        )

    async def delete_access(self, **params: Any) -> Any:
        return await Space.delete_space_access_async(
            self._user_id, self._company_id, self.id, **params
        )

    # ------------------------------------------------------------------
    # Chat / message operations within this space
    # ------------------------------------------------------------------

    async def create_message(self, **params: Any) -> Any:
        return await Space.create_message_async(
            self._user_id, self._company_id, **params
        )

    async def get_messages(self, chat_id: str, **params: Any) -> Any:
        return await Space.get_chat_messages_async(
            self._user_id, self._company_id, chat_id, **params
        )

    async def get_latest_message(self, chat_id: str) -> Any:
        return await Space.get_latest_message_async(
            self._user_id, self._company_id, chat_id
        )

    async def delete_chat(self, chat_id: str) -> Any:
        return await Space.delete_chat_async(
            self._user_id, self._company_id, chat_id
        )


class SpaceManager(BaseManager):
    """Create and retrieve Unique spaces."""

    async def get(self, space_id: str) -> SpaceObject:
        result = await Space.get_space_async(
            self._user_id, self._company_id, space_id
        )
        return SpaceObject(self._user_id, self._company_id, result)

    async def create(self, **params: Any) -> SpaceObject:
        result = await Space.create_space_async(
            self._user_id, self._company_id, **params
        )
        return SpaceObject(self._user_id, self._company_id, result)

    async def update(self, space_id: str, **params: Any) -> SpaceObject:
        result = await Space.update_space_async(
            self._user_id, self._company_id, space_id, **params
        )
        return SpaceObject(self._user_id, self._company_id, result)

    async def delete(self, space_id: str) -> Any:
        return await Space.delete_space_async(
            self._user_id, self._company_id, space_id
        )

    async def create_message(self, **params: Any) -> Any:
        return await Space.create_message_async(
            self._user_id, self._company_id, **params
        )

    async def get_messages(self, chat_id: str, **params: Any) -> Any:
        return await Space.get_chat_messages_async(
            self._user_id, self._company_id, chat_id, **params
        )

    async def get_latest_message(self, chat_id: str) -> Any:
        return await Space.get_latest_message_async(
            self._user_id, self._company_id, chat_id
        )

    async def delete_chat(self, chat_id: str) -> Any:
        return await Space.delete_chat_async(
            self._user_id, self._company_id, chat_id
        )
