"""Low-level function wrappers around :mod:`unique_sdk.Group`.

Each SDK operation gets a ``<verb>`` and ``<verb>_async`` pair. The functions
take ``user_id`` and ``company_id`` as the first two positional arguments (the
acting user's credentials) and return toolkit Pydantic models — SDK
``TypedDict``s never leak out of this module.
"""

from __future__ import annotations

from typing import Any

from unique_sdk import Group

from unique_toolkit.experimental.resources.groups.schemas import (
    GroupDeleted,
    GroupInfo,
    GroupMembership,
    GroupWithConfiguration,
)

DEFAULT_LIST_SKIP = 0
DEFAULT_LIST_TAKE = 100


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
