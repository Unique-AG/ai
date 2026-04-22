"""``unique_toolkit.experimental.identity`` — user and group directory management.

.. warning::

    **Experimental.** This subpackage is exposed under
    :mod:`unique_toolkit.experimental` and its public API may change without
    notice. It is not covered by the toolkit's normal stability guarantees.

A thin, Linux-inspired wrapper around :mod:`unique_sdk.User` and
:mod:`unique_sdk.Group`. The package exposes:

- :class:`Identity` — facade that bundles both sub-services behind
  ``.users`` and ``.groups``.
- :class:`Users` — CRUD-style API for users (``list``, ``get``,
  ``update_configuration``) plus ``groups_of`` / ``is_member``.
- :class:`Groups` — CRUD-style API for groups (``list``, ``create``,
  ``delete``, ``rename``, ``update_configuration``) plus
  ``add_members`` / ``remove_members``.

The Pydantic response schemas (``UserInfo``, ``GroupInfo``, ...) are also
re-exported here for convenience.
"""

from unique_toolkit.experimental.identity.schemas import (
    GroupDeleted,
    GroupInfo,
    GroupMember,
    GroupMembership,
    GroupWithConfiguration,
    UserGroupMembership,
    UserInfo,
    UserWithConfiguration,
)
from unique_toolkit.experimental.identity.service import Groups, Identity, Users

__all__ = [
    "GroupDeleted",
    "GroupInfo",
    "GroupMember",
    "GroupMembership",
    "GroupWithConfiguration",
    "Groups",
    "Identity",
    "UserGroupMembership",
    "UserInfo",
    "UserWithConfiguration",
    "Users",
]
