from typing import Any

from unique_sdk.api_resources._user import User

from .._base import BaseManager, DomainObject


class UserObject(DomainObject):
    """A platform user."""

    async def get_groups(self) -> Any:
        return await User.get_user_groups_async(
            self._user_id, self._company_id, self.id
        )

    async def update_configuration(self, **params: Any) -> "UserObject":
        result = await User.update_user_configuration_async(
            self._user_id, self._company_id, **params
        )
        self._update_raw(result)
        return self


class UserManager(BaseManager):
    """Retrieve and manage platform users."""

    async def list(self, **params: Any) -> Any:
        return await User.get_users_async(self._user_id, self._company_id, **params)

    async def get(self, target_user_id: str) -> UserObject:
        result = await User.get_by_id_async(
            self._user_id, self._company_id, target_user_id
        )
        return UserObject(self._user_id, self._company_id, result)

    async def get_groups(self, target_user_id: str) -> Any:
        return await User.get_user_groups_async(
            self._user_id, self._company_id, target_user_id
        )

    async def update_configuration(self, **params: Any) -> Any:
        return await User.update_user_configuration_async(
            self._user_id, self._company_id, **params
        )
