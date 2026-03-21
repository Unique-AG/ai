from typing import Any

from unique_sdk.api_resources._group import Group

from .._base import BaseManager, DomainObject


class GroupObject(DomainObject):
    """A user group with membership and configuration methods."""

    async def update(self, **params: Any) -> "GroupObject":
        result = await Group.update_group_async(
            self._user_id, self._company_id, self.id, **params
        )
        self._update_raw(result)
        return self

    async def delete(self) -> Any:
        return await Group.delete_group_async(
            self._user_id, self._company_id, self.id
        )

    async def add_users(self, **params: Any) -> Any:
        return await Group.add_users_to_group_async(
            self._user_id, self._company_id, self.id, **params
        )

    async def remove_users(self, **params: Any) -> Any:
        return await Group.remove_users_from_group_async(
            self._user_id, self._company_id, self.id, **params
        )

    async def update_configuration(self, **params: Any) -> Any:
        return await Group.update_group_configuration_async(
            self._user_id, self._company_id, self.id, **params
        )


class GroupManager(BaseManager):
    """Create and manage user groups."""

    async def list(self, **params: Any) -> Any:
        return await Group.get_groups_async(self._user_id, self._company_id, **params)

    async def create(self, **params: Any) -> GroupObject:
        result = await Group.create_group_async(
            self._user_id, self._company_id, **params
        )
        return GroupObject(self._user_id, self._company_id, result)

    async def delete(self, group_id: str) -> Any:
        return await Group.delete_group_async(
            self._user_id, self._company_id, group_id
        )

    async def update(self, group_id: str, **params: Any) -> GroupObject:
        result = await Group.update_group_async(
            self._user_id, self._company_id, group_id, **params
        )
        return GroupObject(self._user_id, self._company_id, result)

    async def add_users(self, group_id: str, **params: Any) -> Any:
        return await Group.add_users_to_group_async(
            self._user_id, self._company_id, group_id, **params
        )

    async def remove_users(self, group_id: str, **params: Any) -> Any:
        return await Group.remove_users_from_group_async(
            self._user_id, self._company_id, group_id, **params
        )

    async def update_configuration(self, group_id: str, **params: Any) -> Any:
        return await Group.update_group_configuration_async(
            self._user_id, self._company_id, group_id, **params
        )
