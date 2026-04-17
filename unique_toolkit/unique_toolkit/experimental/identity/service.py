"""The :class:`Identity` service — users + groups in one place.

.. warning::

    **Experimental.** Lives under :mod:`unique_toolkit.experimental`. The
    public API, method names, and return shapes may change without notice
    and are not covered by the toolkit's normal stability guarantees.

Provides a small, Linux-inspired API on top of :mod:`unique_sdk.User` and
:mod:`unique_sdk.Group`:

- :meth:`Identity.list_users` / :meth:`Identity.list_groups` — listing (``getent``).
- :meth:`Identity.get_user` / :meth:`Identity.groups_of` — single-user lookups
  (``id`` / ``groups``), accept id, email, or username via overloads.
- :meth:`Identity.is_member` — convenience derived from :meth:`groups_of`.
- :meth:`Identity.create_group` / :meth:`Identity.delete_group` /
  :meth:`Identity.rename_group` — group CRUD (``groupadd`` / ``groupdel`` /
  ``groupmod -n``).
- :meth:`Identity.add_members` / :meth:`Identity.remove_members` — bulk
  membership management (``gpasswd -a`` / ``gpasswd -d``).
- :meth:`Identity.update_user_configuration` /
  :meth:`Identity.update_group_configuration` — replace the free-form
  configuration blob.

Every sync method has a matching ``*_async`` sibling.

.. note::

    The SDK does **not** expose create/delete for users; user provisioning
    happens upstream in the directory (SCIM/SSO). This service is read-only for
    users except for the configuration blob.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self, overload

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.experimental.identity.functions import (
    add_group_members,
    add_group_members_async,
    create_group,
    create_group_async,
    delete_group,
    delete_group_async,
    find_user,
    find_user_async,
    get_user_by_id,
    get_user_by_id_async,
    get_user_groups,
    get_user_groups_async,
    list_groups,
    list_groups_async,
    list_users,
    list_users_async,
    remove_group_members,
    remove_group_members_async,
    rename_group,
    rename_group_async,
    update_group_configuration,
    update_group_configuration_async,
    update_user_configuration,
    update_user_configuration_async,
)
from unique_toolkit.experimental.identity.schemas import (
    GroupDeleted,
    GroupInfo,
    GroupMembership,
    GroupWithConfiguration,
    UserGroupMembership,
    UserInfo,
    UserWithConfiguration,
)

if TYPE_CHECKING:
    from unique_toolkit.app.unique_settings import UniqueContext


class Identity:
    """Unified users & groups service for a ``(company_id, user_id)`` context.

    .. warning::

        **Experimental.** Import path is :mod:`unique_toolkit.experimental.identity`.
        The API may change without notice.

    **User identifiers** — :meth:`get_user` and :meth:`groups_of` accept exactly
    one of ``user_id=``, ``email=``, or ``user_name=``. Type checkers enforce
    this via :mod:`typing.overload`; runtime enforcement raises :class:`TypeError`.

    **Group identifiers** — group operations take ``group_id`` (the canonical
    id). If you only know the group name, resolve it first via :meth:`list_groups`
    with ``name=`` or ``find_group`` (to be added if needed).

    **Acting user** — every API call is made on behalf of the user bound to the
    service (``self._user_id``). That user needs the usual directory
    permissions; most read calls are open to any authenticated user, group
    mutations require admin-equivalent rights.
    """

    def __init__(
        self,
        company_id: str,
        user_id: str,
    ) -> None:
        [company_id, user_id] = validate_required_values([company_id, user_id])
        self._company_id = company_id
        self._user_id = user_id

    # ── Construction ──────────────────────────────────────────────────────

    @classmethod
    def from_context(cls, context: UniqueContext) -> Self:
        """Create from a :class:`UniqueContext` (preferred constructor)."""
        return cls(
            company_id=context.auth.get_confidential_company_id(),
            user_id=context.auth.get_confidential_user_id(),
        )

    @classmethod
    def from_settings(
        cls,
        settings: UniqueSettings,
    ) -> Self:
        """Create from :class:`UniqueSettings` (used by :class:`UniqueServiceFactory`)."""

        return cls(
            company_id=settings.authcontext.get_confidential_company_id(),
            user_id=settings.authcontext.get_confidential_user_id(),
        )

    # ── Users: list / get (`getent passwd`, `id <user>`) ──────────────────

    def list_users(
        self,
        *,
        skip: int | None = None,
        take: int | None = None,
        email: str | None = None,
        display_name: str | None = None,
        user_name: str | None = None,
    ) -> list[UserInfo]:
        """List users, optionally filtered server-side (``getent passwd``)."""
        return list_users(
            user_id=self._user_id,
            company_id=self._company_id,
            skip=skip,
            take=take,
            email=email,
            display_name=display_name,
            user_name=user_name,
        )

    async def list_users_async(
        self,
        *,
        skip: int | None = None,
        take: int | None = None,
        email: str | None = None,
        display_name: str | None = None,
        user_name: str | None = None,
    ) -> list[UserInfo]:
        """Async :meth:`list_users`."""
        return await list_users_async(
            user_id=self._user_id,
            company_id=self._company_id,
            skip=skip,
            take=take,
            email=email,
            display_name=display_name,
            user_name=user_name,
        )

    @overload
    def get_user(self, *, user_id: str) -> UserInfo: ...

    @overload
    def get_user(self, *, email: str) -> UserInfo: ...

    @overload
    def get_user(self, *, user_name: str) -> UserInfo: ...

    def get_user(
        self,
        *,
        user_id: str | None = None,
        email: str | None = None,
        user_name: str | None = None,
    ) -> UserInfo:
        """Like ``id <user>`` — look up by id, email, or username (exactly one).

        :raises TypeError: when zero or more than one identifier is supplied.
        :raises LookupError: when ``email=`` or ``user_name=`` is unique-invariant-
            violating (zero or multiple matches).
        """
        kind, value = self._resolve_user_identifier(
            user_id=user_id, email=email, user_name=user_name
        )
        if kind == "id":
            return get_user_by_id(
                user_id=self._user_id,
                company_id=self._company_id,
                target_user_id=value,
            )
        return find_user(
            user_id=self._user_id,
            company_id=self._company_id,
            email=value if kind == "email" else None,
            user_name=value if kind == "user_name" else None,
        )

    @overload
    async def get_user_async(self, *, user_id: str) -> UserInfo: ...

    @overload
    async def get_user_async(self, *, email: str) -> UserInfo: ...

    @overload
    async def get_user_async(self, *, user_name: str) -> UserInfo: ...

    async def get_user_async(
        self,
        *,
        user_id: str | None = None,
        email: str | None = None,
        user_name: str | None = None,
    ) -> UserInfo:
        """Async :meth:`get_user` (same three overload shapes)."""
        kind, value = self._resolve_user_identifier(
            user_id=user_id, email=email, user_name=user_name
        )
        if kind == "id":
            return await get_user_by_id_async(
                user_id=self._user_id,
                company_id=self._company_id,
                target_user_id=value,
            )
        return await find_user_async(
            user_id=self._user_id,
            company_id=self._company_id,
            email=value if kind == "email" else None,
            user_name=value if kind == "user_name" else None,
        )

    # ── Users: groups / membership (`groups <user>`, `id -nG`) ────────────

    @overload
    def groups_of(self, *, user_id: str) -> list[UserGroupMembership]: ...

    @overload
    def groups_of(self, *, email: str) -> list[UserGroupMembership]: ...

    @overload
    def groups_of(self, *, user_name: str) -> list[UserGroupMembership]: ...

    def groups_of(
        self,
        *,
        user_id: str | None = None,
        email: str | None = None,
        user_name: str | None = None,
    ) -> list[UserGroupMembership]:
        """List the groups the given user belongs to (``groups <user>``)."""
        target_id = self._user_id_from_any(
            user_id=user_id, email=email, user_name=user_name
        )
        return get_user_groups(
            user_id=self._user_id,
            company_id=self._company_id,
            target_user_id=target_id,
        )

    @overload
    async def groups_of_async(self, *, user_id: str) -> list[UserGroupMembership]: ...

    @overload
    async def groups_of_async(self, *, email: str) -> list[UserGroupMembership]: ...

    @overload
    async def groups_of_async(self, *, user_name: str) -> list[UserGroupMembership]: ...

    async def groups_of_async(
        self,
        *,
        user_id: str | None = None,
        email: str | None = None,
        user_name: str | None = None,
    ) -> list[UserGroupMembership]:
        """Async :meth:`groups_of`."""
        target_id = await self._user_id_from_any_async(
            user_id=user_id, email=email, user_name=user_name
        )
        return await get_user_groups_async(
            user_id=self._user_id,
            company_id=self._company_id,
            target_user_id=target_id,
        )

    def is_member(self, *, user_id: str, group_id: str) -> bool:
        """Return ``True`` iff the user belongs to the group.

        Implemented client-side via :meth:`groups_of`; O(|user's groups|).
        """
        memberships = self.groups_of(user_id=user_id)
        return any(g.id == group_id for g in memberships)

    async def is_member_async(self, *, user_id: str, group_id: str) -> bool:
        """Async :meth:`is_member`."""
        memberships = await self.groups_of_async(user_id=user_id)
        return any(g.id == group_id for g in memberships)

    # ── Users: configuration (`usermod` for the config blob) ──────────────

    def update_user_configuration(
        self,
        *,
        configuration: dict[str, Any],
        target_user_id: str | None = None,
    ) -> UserWithConfiguration:
        """Replace the configuration blob of the acting user (or ``target_user_id``).

        The underlying endpoint only authorises ``target_user_id == self._user_id``.
        The parameter exists for completeness but most callers can omit it.
        """
        return update_user_configuration(
            user_id=self._user_id,
            company_id=self._company_id,
            target_user_id=target_user_id or self._user_id,
            configuration=configuration,
        )

    async def update_user_configuration_async(
        self,
        *,
        configuration: dict[str, Any],
        target_user_id: str | None = None,
    ) -> UserWithConfiguration:
        """Async :meth:`update_user_configuration`."""
        return await update_user_configuration_async(
            user_id=self._user_id,
            company_id=self._company_id,
            target_user_id=target_user_id or self._user_id,
            configuration=configuration,
        )

    # ── Groups: list / create / delete / rename ───────────────────────────

    def list_groups(
        self,
        *,
        skip: int | None = None,
        take: int | None = None,
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

    async def list_groups_async(
        self,
        *,
        skip: int | None = None,
        take: int | None = None,
        name: str | None = None,
    ) -> list[GroupInfo]:
        """Async :meth:`list_groups`."""
        return await list_groups_async(
            user_id=self._user_id,
            company_id=self._company_id,
            skip=skip,
            take=take,
            name=name,
        )

    def create_group(
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

    async def create_group_async(
        self,
        *,
        name: str,
        parent_id: str | None = None,
        external_id: str | None = None,
    ) -> GroupInfo:
        """Async :meth:`create_group`."""
        return await create_group_async(
            user_id=self._user_id,
            company_id=self._company_id,
            name=name,
            parent_id=parent_id,
            external_id=external_id,
        )

    def delete_group(self, group_id: str) -> GroupDeleted:
        """Delete a group (``groupdel``)."""
        return delete_group(
            user_id=self._user_id,
            company_id=self._company_id,
            group_id=group_id,
        )

    async def delete_group_async(self, group_id: str) -> GroupDeleted:
        """Async :meth:`delete_group`."""
        return await delete_group_async(
            user_id=self._user_id,
            company_id=self._company_id,
            group_id=group_id,
        )

    def rename_group(self, group_id: str, *, new_name: str) -> GroupInfo:
        """Rename a group (``groupmod -n``)."""
        return rename_group(
            user_id=self._user_id,
            company_id=self._company_id,
            group_id=group_id,
            new_name=new_name,
        )

    async def rename_group_async(self, group_id: str, *, new_name: str) -> GroupInfo:
        """Async :meth:`rename_group`."""
        return await rename_group_async(
            user_id=self._user_id,
            company_id=self._company_id,
            group_id=group_id,
            new_name=new_name,
        )

    def update_group_configuration(
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

    async def update_group_configuration_async(
        self,
        group_id: str,
        *,
        configuration: dict[str, Any],
    ) -> GroupWithConfiguration:
        """Async :meth:`update_group_configuration`."""
        return await update_group_configuration_async(
            user_id=self._user_id,
            company_id=self._company_id,
            group_id=group_id,
            configuration=configuration,
        )

    # ── Groups: membership (`gpasswd -a/-d`) ──────────────────────────────

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

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _resolve_user_identifier(
        *,
        user_id: str | None,
        email: str | None,
        user_name: str | None,
    ) -> tuple[str, str]:
        """Return ``(kind, value)`` for the single identifier supplied.

        ``kind`` is one of ``"id" | "email" | "user_name"``.
        """
        provided = [
            ("id", user_id),
            ("email", email),
            ("user_name", user_name),
        ]
        non_null = [(k, v) for k, v in provided if v is not None]
        if len(non_null) == 0:
            raise TypeError("Pass exactly one of user_id=, email=, or user_name=.")
        if len(non_null) > 1:
            keys = ", ".join(k for k, _ in non_null)
            raise TypeError(
                f"Pass exactly one of user_id=, email=, or user_name= (got: {keys})."
            )
        return non_null[0]

    def _user_id_from_any(
        self,
        *,
        user_id: str | None,
        email: str | None,
        user_name: str | None,
    ) -> str:
        kind, value = self._resolve_user_identifier(
            user_id=user_id, email=email, user_name=user_name
        )
        if kind == "id":
            return value
        match = find_user(
            user_id=self._user_id,
            company_id=self._company_id,
            email=value if kind == "email" else None,
            user_name=value if kind == "user_name" else None,
        )
        return match.id

    async def _user_id_from_any_async(
        self,
        *,
        user_id: str | None,
        email: str | None,
        user_name: str | None,
    ) -> str:
        kind, value = self._resolve_user_identifier(
            user_id=user_id, email=email, user_name=user_name
        )
        if kind == "id":
            return value
        match = await find_user_async(
            user_id=self._user_id,
            company_id=self._company_id,
            email=value if kind == "email" else None,
            user_name=value if kind == "user_name" else None,
        )
        return match.id
