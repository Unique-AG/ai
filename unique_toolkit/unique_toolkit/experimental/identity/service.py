"""The :class:`Identity` service — users + groups in one place.

.. warning::

    **Experimental.** Lives under :mod:`unique_toolkit.experimental`. The
    public API, method names, and return shapes may change without notice
    and are not covered by the toolkit's normal stability guarantees.

The package exposes three classes:

- :class:`Users` — CRUD-style API over :mod:`unique_sdk.User` (``list``,
  ``get``, ``update_configuration``) plus the relational helpers
  :meth:`Users.groups_of` and :meth:`Users.is_member`.
- :class:`Groups` — CRUD-style API over :mod:`unique_sdk.Group` (``list``,
  ``create``, ``delete``, ``rename``, ``update_configuration``) plus the
  membership mutators :meth:`Groups.add_members` /
  :meth:`Groups.remove_members`.
- :class:`Identity` — a thin facade that bundles both sub-services behind
  ``.users`` and ``.groups`` so callers can instantiate one object for the
  entire directory surface.

All constructors are **keyword-only** so the ``(user_id, company_id)`` vs
``(company_id, user_id)`` ordering is a non-issue; callers always write
``Users(user_id=..., company_id=...)``. Every sync method has a matching
``*_async`` sibling.

.. note::

    The SDK does **not** expose create/delete for users; user provisioning
    happens upstream in the directory (SCIM/SSO). :class:`Users` is therefore
    read-only apart from :meth:`Users.update_configuration`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self, overload

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.experimental.identity.functions import (
    DEFAULT_LIST_SKIP,
    DEFAULT_LIST_TAKE,
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


# ── Users service ─────────────────────────────────────────────────────────────


class Users:
    """CRUD-style API for users.

    .. warning::

        **Experimental.** Part of :mod:`unique_toolkit.experimental.identity`.
        The API may change without notice.

    Surface:

    - :meth:`list` — paginated listing, optional server-side filters.
    - :meth:`get` — single-user lookup by id, email, or username (overloads).
    - :meth:`update_configuration` — replace the acting user's configuration
      blob. Raises :class:`ValueError` if a different ``target_user_id`` is
      requested, because the SDK endpoint only authorises self-updates.
    - :meth:`groups_of` / :meth:`is_member` — relational helpers that answer
      "what groups is this user in?" / "is this user in that group?".
    """

    def __init__(self, *, user_id: str, company_id: str) -> None:
        [user_id, company_id] = validate_required_values([user_id, company_id])
        self._user_id = user_id
        self._company_id = company_id

    # ── Read: list / get ──────────────────────────────────────────────────

    def list(
        self,
        *,
        skip: int = DEFAULT_LIST_SKIP,
        take: int = DEFAULT_LIST_TAKE,
        email: str | None = None,
        display_name: str | None = None,
        user_name: str | None = None,
    ) -> list[UserInfo]:
        """List users, optionally filtered server-side (``getent passwd``).

        ``skip``/``take`` default to a 0/:data:`~unique_toolkit.experimental.identity.functions.DEFAULT_LIST_TAKE`
        pagination window; callers can widen or shrink it as needed.
        """
        return list_users(
            user_id=self._user_id,
            company_id=self._company_id,
            skip=skip,
            take=take,
            email=email,
            display_name=display_name,
            user_name=user_name,
        )

    async def list_async(
        self,
        *,
        skip: int = DEFAULT_LIST_SKIP,
        take: int = DEFAULT_LIST_TAKE,
        email: str | None = None,
        display_name: str | None = None,
        user_name: str | None = None,
    ) -> list[UserInfo]:
        """Async :meth:`list`."""
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
    def get(self, *, user_id: str) -> UserInfo: ...

    @overload
    def get(self, *, email: str) -> UserInfo: ...

    @overload
    def get(self, *, user_name: str) -> UserInfo: ...

    def get(
        self,
        *,
        user_id: str | None = None,
        email: str | None = None,
        user_name: str | None = None,
    ) -> UserInfo:
        """Look up a single user by id, email, or username (exactly one).

        :raises TypeError: when zero or more than one identifier is supplied.
        :raises LookupError: when ``email=`` or ``user_name=`` yields zero or
            multiple matches.
        """
        kind, value = _resolve_user_identifier(
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
    async def get_async(self, *, user_id: str) -> UserInfo: ...

    @overload
    async def get_async(self, *, email: str) -> UserInfo: ...

    @overload
    async def get_async(self, *, user_name: str) -> UserInfo: ...

    async def get_async(
        self,
        *,
        user_id: str | None = None,
        email: str | None = None,
        user_name: str | None = None,
    ) -> UserInfo:
        """Async :meth:`get` (same three overload shapes)."""
        kind, value = _resolve_user_identifier(
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

    # ── Write: configuration (self-only) ──────────────────────────────────

    def update_configuration(
        self,
        *,
        configuration: dict[str, Any],
        target_user_id: str | None = None,
    ) -> UserWithConfiguration:
        """Replace the configuration blob of the acting user.

        The underlying endpoint only authorises updating the acting user's own
        configuration. ``target_user_id`` exists for API symmetry but, when
        provided, must equal ``self._user_id`` — otherwise :class:`ValueError`
        is raised by :func:`update_user_configuration` to avoid silently
        ignoring the caller's intent.

        :raises ValueError: when ``target_user_id`` is set and differs from
            the service's acting user.
        """
        effective_target = self._user_id if target_user_id is None else target_user_id
        return update_user_configuration(
            user_id=self._user_id,
            company_id=self._company_id,
            target_user_id=effective_target,
            configuration=configuration,
        )

    async def update_configuration_async(
        self,
        *,
        configuration: dict[str, Any],
        target_user_id: str | None = None,
    ) -> UserWithConfiguration:
        """Async :meth:`update_configuration`.

        :raises ValueError: when ``target_user_id`` is set and differs from
            the service's acting user. See :meth:`update_configuration`.
        """
        effective_target = self._user_id if target_user_id is None else target_user_id
        return await update_user_configuration_async(
            user_id=self._user_id,
            company_id=self._company_id,
            target_user_id=effective_target,
            configuration=configuration,
        )

    # ── Relations: groups_of / is_member ──────────────────────────────────

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

    # ── Private helpers ───────────────────────────────────────────────────

    def _user_id_from_any(
        self,
        *,
        user_id: str | None,
        email: str | None,
        user_name: str | None,
    ) -> str:
        kind, value = _resolve_user_identifier(
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
        kind, value = _resolve_user_identifier(
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


# ── Groups service ────────────────────────────────────────────────────────────


class Groups:
    """CRUD-style API for groups plus membership mutators.

    .. warning::

        **Experimental.** Part of :mod:`unique_toolkit.experimental.identity`.
        The API may change without notice.

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

    # ── Read ──────────────────────────────────────────────────────────────

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

    # ── Write: lifecycle ──────────────────────────────────────────────────

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

    # ── Write: membership ────────────────────────────────────────────────

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


# ── Identity facade ───────────────────────────────────────────────────────────


class Identity:
    """Unified users + groups facade for a ``(user_id, company_id)`` context.

    .. warning::

        **Experimental.** Import path is :mod:`unique_toolkit.experimental.identity`.
        The API may change without notice.

    :class:`Identity` owns two sub-services:

    - :attr:`users` — an instance of :class:`Users`.
    - :attr:`groups` — an instance of :class:`Groups`.

    ``Identity`` itself is stateless beyond the credentials it holds; the
    actual CRUD surface lives on the sub-services so callers write
    ``identity.users.list()`` or ``identity.groups.add_members(...)``. Both
    sub-services share the same ``(user_id, company_id)`` pair, so
    instantiating :class:`Identity` is equivalent to building both
    sub-services manually.

    **Acting user** — every API call is made on behalf of ``user_id``. That
    user needs the usual directory permissions; most reads are open to any
    authenticated user, group mutations require admin-equivalent rights.
    """

    def __init__(self, *, user_id: str, company_id: str) -> None:
        [user_id, company_id] = validate_required_values([user_id, company_id])
        self._user_id = user_id
        self._company_id = company_id
        self._users = Users(user_id=user_id, company_id=company_id)
        self._groups = Groups(user_id=user_id, company_id=company_id)

    # ── Construction ──────────────────────────────────────────────────────

    @classmethod
    def from_context(cls, context: UniqueContext) -> Self:
        """Create from a :class:`UniqueContext` (preferred constructor)."""
        return cls(
            user_id=context.auth.get_confidential_user_id(),
            company_id=context.auth.get_confidential_company_id(),
        )

    @classmethod
    def from_settings(
        cls,
        settings: UniqueSettings | str | None = None,
        **_kwargs: Any,
    ) -> Self:
        """Create from :class:`UniqueSettings` (used by :class:`UniqueServiceFactory`).

        Mirrors :meth:`KnowledgeBaseService.from_settings` so callers can write
        ``Identity.from_settings()`` in standalone scripts:

        - ``settings=None`` auto-loads from ``unique.env`` via
          :meth:`UniqueSettings.from_env_auto_with_sdk_init`.
        - ``settings="my.env"`` loads from the given env file name.
        - ``settings=<UniqueSettings>`` uses the provided instance as-is.

        ``**_kwargs`` is accepted and ignored so :class:`UniqueServiceFactory`
        can call ``Identity.from_settings(settings, **kwargs)`` uniformly
        alongside services that do consume extra kwargs.
        """
        if settings is None:
            settings = UniqueSettings.from_env_auto_with_sdk_init()
        elif isinstance(settings, str):
            settings = UniqueSettings.from_env_auto_with_sdk_init(filename=settings)

        return cls(
            user_id=settings.authcontext.get_confidential_user_id(),
            company_id=settings.authcontext.get_confidential_company_id(),
        )

    @property
    def users(self) -> Users:
        return self._users

    @property
    def groups(self) -> Groups:
        return self._groups


# ── Module-private helpers ────────────────────────────────────────────────────


def _resolve_user_identifier(
    *,
    user_id: str | None,
    email: str | None,
    user_name: str | None,
) -> tuple[str, str]:
    """Return ``(kind, value)`` for the single identifier supplied.

    ``kind`` is one of ``"id" | "email" | "user_name"``. Raises
    :class:`TypeError` when zero or more than one identifier is non-``None``.
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
