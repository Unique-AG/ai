"""The :class:`Groups` service.

.. warning::

    **Experimental.** Lives under :mod:`unique_toolkit.experimental`. The
    public API may change without notice.

CRUD-style API over :mod:`unique_sdk.Group` plus the bulk membership
mutators :meth:`Groups.add_members` / :meth:`Groups.remove_members`.

All constructors are **keyword-only**; every sync method has a matching
``*_async`` sibling.
"""

from __future__ import annotations

from typing import Any

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.experimental.resources.group.functions import (
    DEFAULT_LIST_SKIP,
    DEFAULT_LIST_TAKE,
    add_group_members,
    add_group_members_async,
    create_group,
    create_group_async,
    delete_group,
    delete_group_async,
    list_groups,
    list_groups_async,
    remove_group_members,
    remove_group_members_async,
    rename_group,
    rename_group_async,
    update_group_configuration,
    update_group_configuration_async,
)
from unique_toolkit.experimental.resources.group.schemas import (
    GroupDeleted,
    GroupInfo,
    GroupMembership,
    GroupWithConfiguration,
)


class Groups:
    """CRUD-style API for groups plus membership mutators.

    .. warning::

        **Experimental.** Part of
        :mod:`unique_toolkit.experimental.resources.group`. The API may
        change without notice.

    Surface:

    - :meth:`list` — paginated listing with optional name filter.
    - :meth:`create` / :meth:`delete` / :meth:`rename` — lifecycle
      (``groupadd`` / ``groupdel`` / ``groupmod -n``).
    - :meth:`update_configuration` — replace a group's free-form configuration
      blob.
    - :meth:`add_members` / :meth:`remove_members` — bulk membership mutation
      (``gpasswd -a`` / ``gpasswd -d``).

    Group identifiers passed to mutating methods are always canonical
    ``group_id`` strings. If you only have a name, resolve it via
    :meth:`list` with ``name=`` first.
    """

    def __init__(self, *, user_id: str, company_id: str) -> None:
        [user_id, company_id] = validate_required_values([user_id, company_id])
        self._user_id = user_id
        self._company_id = company_id

    def list(
        self,
        *,
        skip: int = DEFAULT_LIST_SKIP,
        take: int = DEFAULT_LIST_TAKE,
        name: str | None = None,
    ) -> list[GroupInfo]:
        """List groups, optionally filtered by name (``getent group``)."""
        return list_groups(
            user_id=self._user_id,
            company_id=self._company_id,
            skip=skip,
            take=take,
            name=name,
        )

    async def list_async(
        self,
        *,
        skip: int = DEFAULT_LIST_SKIP,
        take: int = DEFAULT_LIST_TAKE,
        name: str | None = None,
    ) -> list[GroupInfo]:
        """Async :meth:`list`."""
        return await list_groups_async(
            user_id=self._user_id,
            company_id=self._company_id,
            skip=skip,
            take=take,
            name=name,
        )

    def create(
        self,
        *,
        name: str,
        parent_id: str | None = None,
        external_id: str | None = None,
    ) -> GroupInfo:
        """Create a group (``groupadd``)."""
        return create_group(
            user_id=self._user_id,
            company_id=self._company_id,
            name=name,
            parent_id=parent_id,
            external_id=external_id,
        )

    async def create_async(
        self,
        *,
        name: str,
        parent_id: str | None = None,
        external_id: str | None = None,
    ) -> GroupInfo:
        """Async :meth:`create`."""
        return await create_group_async(
            user_id=self._user_id,
            company_id=self._company_id,
            name=name,
            parent_id=parent_id,
            external_id=external_id,
        )

    def delete(self, group_id: str) -> GroupDeleted:
        """Delete a group (``groupdel``)."""
        return delete_group(
            user_id=self._user_id,
            company_id=self._company_id,
            group_id=group_id,
        )

    async def delete_async(self, group_id: str) -> GroupDeleted:
        """Async :meth:`delete`."""
        return await delete_group_async(
            user_id=self._user_id,
            company_id=self._company_id,
            group_id=group_id,
        )

    def rename(self, group_id: str, *, new_name: str) -> GroupInfo:
        """Rename a group (``groupmod -n``)."""
        return rename_group(
            user_id=self._user_id,
            company_id=self._company_id,
            group_id=group_id,
            new_name=new_name,
        )

    async def rename_async(self, group_id: str, *, new_name: str) -> GroupInfo:
        """Async :meth:`rename`."""
        return await rename_group_async(
            user_id=self._user_id,
            company_id=self._company_id,
            group_id=group_id,
            new_name=new_name,
        )

    def update_configuration(
        self,
        group_id: str,
        *,
        configuration: dict[str, Any],
    ) -> GroupWithConfiguration:
        """Replace the configuration blob of a group."""
        return update_group_configuration(
            user_id=self._user_id,
            company_id=self._company_id,
            group_id=group_id,
            configuration=configuration,
        )

    async def update_configuration_async(
        self,
        group_id: str,
        *,
        configuration: dict[str, Any],
    ) -> GroupWithConfiguration:
        """Async :meth:`update_configuration`."""
        return await update_group_configuration_async(
            user_id=self._user_id,
            company_id=self._company_id,
            group_id=group_id,
            configuration=configuration,
        )

    def add_members(
        self,
        group_id: str,
        *,
        user_ids: list[str],
    ) -> list[GroupMembership]:
        """Add users to a group (``gpasswd -a`` / ``usermod -aG``). Bulk."""
        return add_group_members(
            user_id=self._user_id,
            company_id=self._company_id,
            group_id=group_id,
            user_ids=user_ids,
        )

    async def add_members_async(
        self,
        group_id: str,
        *,
        user_ids: list[str],
    ) -> list[GroupMembership]:
        """Async :meth:`add_members`."""
        return await add_group_members_async(
            user_id=self._user_id,
            company_id=self._company_id,
            group_id=group_id,
            user_ids=user_ids,
        )

    def remove_members(
        self,
        group_id: str,
        *,
        user_ids: list[str],
    ) -> bool:
        """Remove users from a group (``gpasswd -d``). Bulk."""
        return remove_group_members(
            user_id=self._user_id,
            company_id=self._company_id,
            group_id=group_id,
            user_ids=user_ids,
        )

    async def remove_members_async(
        self,
        group_id: str,
        *,
        user_ids: list[str],
    ) -> bool:
        """Async :meth:`remove_members`."""
        return await remove_group_members_async(
            user_id=self._user_id,
            company_id=self._company_id,
            group_id=group_id,
            user_ids=user_ids,
        )
