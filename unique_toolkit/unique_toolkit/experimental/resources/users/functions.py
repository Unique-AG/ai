"""Low-level function wrappers around :mod:`unique_sdk.User`.

Each SDK operation gets a ``<verb>`` and ``<verb>_async`` pair. The functions
take ``user_id`` and ``company_id`` as the first two positional arguments (the
acting user's credentials) and return toolkit Pydantic models — SDK
``TypedDict``s never leak out of this module.
"""

from __future__ import annotations

from typing import Any

from unique_sdk import User

from unique_toolkit.experimental.resources.users.schemas import (
    UserGroupMembership,
    UserInfo,
    UserWithConfiguration,
)

DEFAULT_LIST_SKIP = 0
DEFAULT_LIST_TAKE = 100

FIND_USER_TAKE = 2


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

    :raises ValueError: when ``target_user_id`` differs from the acting
        ``user_id`` — the underlying SDK endpoint only updates the acting
        user's own configuration, so any other target would be silently
        ignored.
    """
    _assert_self_update(user_id=user_id, target_user_id=target_user_id)
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
    """Async :func:`update_user_configuration`.

    :raises ValueError: when ``target_user_id`` differs from the acting
        ``user_id``. See :func:`update_user_configuration` for rationale.
    """
    _assert_self_update(user_id=user_id, target_user_id=target_user_id)
    payload = await User.update_user_configuration_async(
        user_id=target_user_id,
        company_id=company_id,
        userConfiguration=configuration,
    )
    return UserWithConfiguration.model_validate(payload, by_alias=True, by_name=True)


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


def _assert_self_update(*, user_id: str, target_user_id: str) -> None:
    """Fail fast when an update-configuration call targets another user.

    ``unique_sdk.User.update_user_configuration`` is authenticated as
    ``user_id`` and always writes to that same user's configuration — the
    ``target_user_id`` would otherwise be silently swapped in as the acting
    user. Raising here keeps the intent of the caller honest.
    """
    if target_user_id != user_id:
        raise ValueError(
            "update_user_configuration: target_user_id must equal user_id; the "
            "underlying SDK endpoint only updates the acting user's own "
            f"configuration (got user_id={user_id!r}, target_user_id={target_user_id!r})."
        )


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
