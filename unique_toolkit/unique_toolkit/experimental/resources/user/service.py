"""The :class:`Users` service.

.. warning::

    **Experimental.** Lives under :mod:`unique_toolkit.experimental`. The
    public API may change without notice.

CRUD-style API over :mod:`unique_sdk.User` plus the relational helpers
:meth:`Users.groups_of` / :meth:`Users.is_member`. The relational methods
stay here because the underlying SDK endpoint is ``GET /users/{id}/groups``
— the response is naturally rooted on the user.

All constructors are **keyword-only**; every sync method has a matching
``*_async`` sibling.

.. note::

    The SDK does **not** expose create/delete for users; user provisioning
    happens upstream in the directory (SCIM/SSO). :class:`Users` is therefore
    read-only apart from :meth:`Users.update_configuration`.
"""

from __future__ import annotations

from typing import Any, overload

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.experimental.resources.user.functions import (
    DEFAULT_LIST_SKIP,
    DEFAULT_LIST_TAKE,
    find_user,
    find_user_async,
    get_user_by_id,
    get_user_by_id_async,
    get_user_groups,
    get_user_groups_async,
    list_users,
    list_users_async,
    update_user_configuration,
    update_user_configuration_async,
)
from unique_toolkit.experimental.resources.user.schemas import (
    UserGroupMembership,
    UserInfo,
    UserWithConfiguration,
)


class Users:
    """CRUD-style API for users.

    .. warning::

        **Experimental.** Part of
        :mod:`unique_toolkit.experimental.resources.user`. The API may
        change without notice.

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

        ``skip``/``take`` default to a 0/:data:`~unique_toolkit.experimental.resources.user.functions.DEFAULT_LIST_TAKE`
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
