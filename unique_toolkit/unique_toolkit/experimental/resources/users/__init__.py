"""Typed wrapper over the ``unique_sdk`` user resource.

Carved out of the original monolithic ``experimental.identity`` package.
Only the user-centric pieces live here:

* :class:`Users` service (from :mod:`.service`)
* functions: :func:`list_users`, :func:`get_user_by_id`, :func:`find_user`,
  :func:`get_user_groups`, :func:`update_user_configuration` (plus their
  ``_async`` siblings, from :mod:`.functions`)
* schemas: :class:`UserInfo`, :class:`UserWithConfiguration`,
  :class:`UserGroupMembership` (from :mod:`.schemas`)

The cross-cutting :meth:`Users.groups_of` / :meth:`Users.is_member` relational
helpers stay on this resource because the SDK's "groups of user" endpoint
hangs off the user entity. The :class:`Identity` facade that composes
:class:`Users` + :class:`~unique_toolkit.experimental.resources.groups.Groups`
lives in :mod:`unique_toolkit.experimental.resources.facades.identity`.
"""

from unique_toolkit.experimental.resources.users.functions import (
    DEFAULT_LIST_SKIP,
    DEFAULT_LIST_TAKE,
    FIND_USER_TAKE,
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
from unique_toolkit.experimental.resources.users.schemas import (
    UserGroupMembership,
    UserInfo,
    UserWithConfiguration,
)
from unique_toolkit.experimental.resources.users.service import Users

__all__ = [
    "DEFAULT_LIST_SKIP",
    "DEFAULT_LIST_TAKE",
    "FIND_USER_TAKE",
    "UserGroupMembership",
    "UserInfo",
    "UserWithConfiguration",
    "Users",
    "find_user",
    "find_user_async",
    "get_user_by_id",
    "get_user_by_id_async",
    "get_user_groups",
    "get_user_groups_async",
    "list_users",
    "list_users_async",
    "update_user_configuration",
    "update_user_configuration_async",
]
