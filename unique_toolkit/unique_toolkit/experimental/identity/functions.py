"""Low-level function wrappers around :mod:`User` and :mod:`Group`.

Each SDK operation gets a ``<verb>`` and ``<verb>_async`` pair. The functions take
``user_id`` and ``company_id`` as the first two positional arguments (the acting
user's credentials) and return toolkit Pydantic models — SDK ``TypedDict``s never
leak out of this module.
"""

from __future__ import annotations

from typing import Any

from unique_sdk import Group, User

from unique_toolkit.experimental.identity.schemas import (
    GroupDeleted,
    GroupInfo,
    GroupMembership,
    GroupWithConfiguration,
    UserGroupMembership,
    UserInfo,
    UserWithConfiguration,
)

# Default pagination window for list endpoints. Small enough to keep latency
# predictable, large enough to avoid round-tripping for typical directories.
DEFAULT_LIST_SKIP = 0
DEFAULT_LIST_TAKE = 100

# ``find_user`` asks for two rows so we can detect ambiguity (zero, one, or
# "more than one") without paging through the entire result set.
FIND_USER_TAKE = 2

# ── User read operations ──────────────────────────────────────────────────────


def list_users(
    user_id: str,
    company_id: str,
    *,
    skip: int = DEFAULT_LIST_SKIP,
    take: int = DEFAULT_LIST_TAKE,
    email: str | None = None,
    display_name: str | None = None,
    user_name: str | None = None,
) -> list[UserInfo]:
    """Page through users in the company.

    ``skip``/``take`` default to a 0/:data:`DEFAULT_LIST_TAKE` window; all other
    filters are optional and omitted from the request when ``None``.
    """
    params = _build_list_users_params(
        skip=skip,
        take=take,
        email=email,
        display_name=display_name,
        user_name=user_name,
    )
    result = User.get_users(user_id=user_id, company_id=company_id, **params)
    return [
        UserInfo.model_validate(u, by_alias=True, by_name=True) for u in result["users"]
    ]


async def list_users_async(
    user_id: str,
    company_id: str,
    *,
    skip: int = DEFAULT_LIST_SKIP,
    take: int = DEFAULT_LIST_TAKE,
    email: str | None = None,
    display_name: str | None = None,
    user_name: str | None = None,
) -> list[UserInfo]:
    """Async :func:`list_users`."""
    params = _build_list_users_params(
        skip=skip,
        take=take,
        email=email,
        display_name=display_name,
        user_name=user_name,
    )
    result = await User.get_users_async(
        user_id=user_id, company_id=company_id, **params
    )
    return [
        UserInfo.model_validate(u, by_alias=True, by_name=True) for u in result["users"]
    ]


def get_user_by_id(
    user_id: str,
    company_id: str,
    *,
    target_user_id: str,
) -> UserInfo:
    """Fetch a single user by canonical id."""
    payload = User.get_by_id(
        user_id=user_id,
        company_id=company_id,
        target_user_id=target_user_id,
    )
    return UserInfo.model_validate(payload, by_alias=True, by_name=True)


async def get_user_by_id_async(
    user_id: str,
    company_id: str,
    *,
    target_user_id: str,
) -> UserInfo:
    """Async :func:`get_user_by_id`."""
    payload = await User.get_by_id_async(
        user_id=user_id,
        company_id=company_id,
        target_user_id=target_user_id,
    )
    return UserInfo.model_validate(payload, by_alias=True, by_name=True)


def find_user(
    user_id: str,
    company_id: str,
    *,
    email: str | None = None,
    user_name: str | None = None,
) -> UserInfo:
    """Resolve a user by email or username using a filtered :func:`list_users` call.

    Raises :class:`LookupError` when the filter matches zero or more than one user.
    """
    if (email is None) == (user_name is None):
        raise TypeError("find_user: pass exactly one of email= or user_name=.")
    matches = list_users(
        user_id=user_id,
        company_id=company_id,
        email=email,
        user_name=user_name,
        take=FIND_USER_TAKE,
    )
    return _only_match(matches, email=email, user_name=user_name)


async def find_user_async(
    user_id: str,
    company_id: str,
    *,
    email: str | None = None,
    user_name: str | None = None,
) -> UserInfo:
    """Async :func:`find_user`."""
    if (email is None) == (user_name is None):
        raise TypeError("find_user: pass exactly one of email= or user_name=.")
    matches = await list_users_async(
        user_id=user_id,
        company_id=company_id,
        email=email,
        user_name=user_name,
        take=FIND_USER_TAKE,
    )
    return _only_match(matches, email=email, user_name=user_name)


def get_user_groups(
    user_id: str,
    company_id: str,
    *,
    target_user_id: str,
) -> list[UserGroupMembership]:
    """List the groups a user belongs to (``groups <user>``)."""
    payload = User.get_user_groups(
        user_id=user_id,
        company_id=company_id,
        target_user_id=target_user_id,
    )
    return [
        UserGroupMembership.model_validate(g, by_alias=True, by_name=True)
        for g in payload["groups"]
    ]


async def get_user_groups_async(
    user_id: str,
    company_id: str,
    *,
    target_user_id: str,
) -> list[UserGroupMembership]:
    """Async :func:`get_user_groups`."""
    payload = await User.get_user_groups_async(
        user_id=user_id,
        company_id=company_id,
        target_user_id=target_user_id,
    )
    return [
        UserGroupMembership.model_validate(g, by_alias=True, by_name=True)
        for g in payload["groups"]
    ]


def update_user_configuration(
    user_id: str,
    company_id: str,
    *,
    target_user_id: str,
    configuration: dict[str, Any],
) -> UserWithConfiguration:
    """Replace the target user's ``user_configuration`` blob.

    The SDK only supports this call for ``target_user_id == user_id`` (the acting
    user). Callers that need to mutate other users' config must delegate to a
    service user.
    """
    payload = User.update_user_configuration(
        user_id=target_user_id,
        company_id=company_id,
        userConfiguration=configuration,
    )
    return UserWithConfiguration.model_validate(payload, by_alias=True, by_name=True)


async def update_user_configuration_async(
    user_id: str,
    company_id: str,
    *,
    target_user_id: str,
    configuration: dict[str, Any],
) -> UserWithConfiguration:
    """Async :func:`update_user_configuration`."""
    payload = await User.update_user_configuration_async(
        user_id=target_user_id,
        company_id=company_id,
        userConfiguration=configuration,
    )
    return UserWithConfiguration.model_validate(payload, by_alias=True, by_name=True)


# ── Group CRUD ────────────────────────────────────────────────────────────────


def list_groups(
    user_id: str,
    company_id: str,
    *,
    skip: int = DEFAULT_LIST_SKIP,
    take: int = DEFAULT_LIST_TAKE,
    name: str | None = None,
) -> list[GroupInfo]:
    """Page through groups in the company (``getent group``).

    ``skip``/``take`` default to a 0/:data:`DEFAULT_LIST_TAKE` window.
    """
    params = _build_list_groups_params(skip=skip, take=take, name=name)
    result = Group.get_groups(user_id=user_id, company_id=company_id, **params)
    return [
        GroupInfo.model_validate(g, by_alias=True, by_name=True)
        for g in result["groups"]
    ]


async def list_groups_async(
    user_id: str,
    company_id: str,
    *,
    skip: int = DEFAULT_LIST_SKIP,
    take: int = DEFAULT_LIST_TAKE,
    name: str | None = None,
) -> list[GroupInfo]:
    """Async :func:`list_groups`."""
    params = _build_list_groups_params(skip=skip, take=take, name=name)
    result = await Group.get_groups_async(
        user_id=user_id, company_id=company_id, **params
    )
    return [
        GroupInfo.model_validate(g, by_alias=True, by_name=True)
        for g in result["groups"]
    ]


def create_group(
    user_id: str,
    company_id: str,
    *,
    name: str,
    parent_id: str | None = None,
    external_id: str | None = None,
) -> GroupInfo:
    """Create a group (``groupadd``)."""
    params = _build_create_group_params(
        name=name, parent_id=parent_id, external_id=external_id
    )
    payload = Group.create_group(user_id=user_id, company_id=company_id, **params)
    return GroupInfo.model_validate(payload, by_alias=True, by_name=True)


async def create_group_async(
    user_id: str,
    company_id: str,
    *,
    name: str,
    parent_id: str | None = None,
    external_id: str | None = None,
) -> GroupInfo:
    """Async :func:`create_group`."""
    params = _build_create_group_params(
        name=name, parent_id=parent_id, external_id=external_id
    )
    payload = await Group.create_group_async(
        user_id=user_id, company_id=company_id, **params
    )
    return GroupInfo.model_validate(payload, by_alias=True, by_name=True)


def delete_group(
    user_id: str,
    company_id: str,
    *,
    group_id: str,
) -> GroupDeleted:
    """Delete a group (``groupdel``)."""
    payload = Group.delete_group(
        user_id=user_id, company_id=company_id, group_id=group_id
    )
    return GroupDeleted.model_validate(payload, by_alias=True, by_name=True)


async def delete_group_async(
    user_id: str,
    company_id: str,
    *,
    group_id: str,
) -> GroupDeleted:
    """Async :func:`delete_group`."""
    payload = await Group.delete_group_async(
        user_id=user_id, company_id=company_id, group_id=group_id
    )
    return GroupDeleted.model_validate(payload, by_alias=True, by_name=True)


def rename_group(
    user_id: str,
    company_id: str,
    *,
    group_id: str,
    new_name: str,
) -> GroupInfo:
    """Rename a group (``groupmod -n``). Name is the only renameable top-level field."""
    payload = Group.update_group(
        user_id=user_id,
        company_id=company_id,
        group_id=group_id,
        name=new_name,
    )
    return GroupInfo.model_validate(payload, by_alias=True, by_name=True)


async def rename_group_async(
    user_id: str,
    company_id: str,
    *,
    group_id: str,
    new_name: str,
) -> GroupInfo:
    """Async :func:`rename_group`."""
    payload = await Group.update_group_async(
        user_id=user_id,
        company_id=company_id,
        group_id=group_id,
        name=new_name,
    )
    return GroupInfo.model_validate(payload, by_alias=True, by_name=True)


def update_group_configuration(
    user_id: str,
    company_id: str,
    *,
    group_id: str,
    configuration: dict[str, Any],
) -> GroupWithConfiguration:
    """Replace a group's free-form configuration blob."""
    payload = Group.update_group_configuration(
        user_id=user_id,
        company_id=company_id,
        group_id=group_id,
        configuration=configuration,
    )
    return GroupWithConfiguration.model_validate(payload, by_alias=True, by_name=True)


async def update_group_configuration_async(
    user_id: str,
    company_id: str,
    *,
    group_id: str,
    configuration: dict[str, Any],
) -> GroupWithConfiguration:
    """Async :func:`update_group_configuration`."""
    payload = await Group.update_group_configuration_async(
        user_id=user_id,
        company_id=company_id,
        group_id=group_id,
        configuration=configuration,
    )
    return GroupWithConfiguration.model_validate(payload, by_alias=True, by_name=True)


# ── Group membership ──────────────────────────────────────────────────────────


def add_group_members(
    user_id: str,
    company_id: str,
    *,
    group_id: str,
    user_ids: list[str],
) -> list[GroupMembership]:
    """Add users to a group (``gpasswd -a``). Bulk."""
    if not user_ids:
        raise ValueError("add_group_members: user_ids must not be empty.")
    payload = Group.add_users_to_group(
        user_id=user_id,
        company_id=company_id,
        group_id=group_id,
        userIds=user_ids,
    )
    return [
        GroupMembership.model_validate(m, by_alias=True, by_name=True)
        for m in payload["memberships"]
    ]


async def add_group_members_async(
    user_id: str,
    company_id: str,
    *,
    group_id: str,
    user_ids: list[str],
) -> list[GroupMembership]:
    """Async :func:`add_group_members`."""
    if not user_ids:
        raise ValueError("add_group_members: user_ids must not be empty.")
    payload = await Group.add_users_to_group_async(
        user_id=user_id,
        company_id=company_id,
        group_id=group_id,
        userIds=user_ids,
    )
    return [
        GroupMembership.model_validate(m, by_alias=True, by_name=True)
        for m in payload["memberships"]
    ]


def remove_group_members(
    user_id: str,
    company_id: str,
    *,
    group_id: str,
    user_ids: list[str],
) -> bool:
    """Remove users from a group (``gpasswd -d``). Returns the API success flag."""
    if not user_ids:
        raise ValueError("remove_group_members: user_ids must not be empty.")
    payload = Group.remove_users_from_group(
        user_id=user_id,
        company_id=company_id,
        group_id=group_id,
        userIds=user_ids,
    )
    return bool(payload["success"])


async def remove_group_members_async(
    user_id: str,
    company_id: str,
    *,
    group_id: str,
    user_ids: list[str],
) -> bool:
    """Async :func:`remove_group_members`."""
    if not user_ids:
        raise ValueError("remove_group_members: user_ids must not be empty.")
    payload = await Group.remove_users_from_group_async(
        user_id=user_id,
        company_id=company_id,
        group_id=group_id,
        userIds=user_ids,
    )
    return bool(payload["success"])


# ── Private helpers ───────────────────────────────────────────────────────────


def _build_list_users_params(
    *,
    skip: int,
    take: int,
    email: str | None,
    display_name: str | None,
    user_name: str | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"skip": skip, "take": take}
    if email is not None:
        params["email"] = email
    if display_name is not None:
        params["displayName"] = display_name
    if user_name is not None:
        params["userName"] = user_name
    return params


def _build_list_groups_params(
    *,
    skip: int,
    take: int,
    name: str | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"skip": skip, "take": take}
    if name is not None:
        params["name"] = name
    return params


def _build_create_group_params(
    *,
    name: str,
    parent_id: str | None,
    external_id: str | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"name": name}
    if parent_id is not None:
        params["parentId"] = parent_id
    if external_id is not None:
        params["externalId"] = external_id
    return params


def _only_match(
    matches: list[UserInfo],
    *,
    email: str | None,
    user_name: str | None,
) -> UserInfo:
    criterion = f"email={email!r}" if email is not None else f"user_name={user_name!r}"
    if len(matches) == 0:
        raise LookupError(f"find_user: no user matches {criterion}.")
    if len(matches) > 1:
        raise LookupError(
            f"find_user: {len(matches)} users match {criterion}; refine the filter."
        )
    return matches[0]
