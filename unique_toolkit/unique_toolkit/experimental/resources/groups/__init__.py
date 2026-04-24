"""Typed wrapper over the ``unique_sdk`` group resource.

Carved out of the original monolithic ``experimental.identity`` package.
Only the group-centric pieces live here:

* :class:`Groups` service (from :mod:`.service`)
* functions: :func:`list_groups`, :func:`create_group`, :func:`delete_group`,
  :func:`rename_group`, :func:`update_group_configuration`,
  :func:`add_group_members`, :func:`remove_group_members` (plus their
  ``_async`` siblings, from :mod:`.functions`)
* schemas: :class:`GroupInfo`, :class:`GroupWithConfiguration`,
  :class:`GroupMember`, :class:`GroupMembership`, :class:`GroupDeleted`
  (from :mod:`.schemas`)

The :class:`Identity` facade that composes
:class:`~unique_toolkit.experimental.resources.users.Users` + :class:`Groups`
lives in :mod:`unique_toolkit.experimental.resources.facades.identity`.
"""

from unique_toolkit.experimental.resources.groups.functions import (
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
from unique_toolkit.experimental.resources.groups.schemas import (
    GroupDeleted,
    GroupInfo,
    GroupMember,
    GroupMembership,
    GroupWithConfiguration,
)
from unique_toolkit.experimental.resources.groups.service import Groups

__all__ = [
    "DEFAULT_LIST_SKIP",
    "DEFAULT_LIST_TAKE",
    "GroupDeleted",
    "GroupInfo",
    "GroupMember",
    "GroupMembership",
    "GroupWithConfiguration",
    "Groups",
    "add_group_members",
    "add_group_members_async",
    "create_group",
    "create_group_async",
    "delete_group",
    "delete_group_async",
    "list_groups",
    "list_groups_async",
    "remove_group_members",
    "remove_group_members_async",
    "rename_group",
    "rename_group_async",
    "update_group_configuration",
    "update_group_configuration_async",
]
