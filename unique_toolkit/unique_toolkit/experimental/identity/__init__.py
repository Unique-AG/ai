"""Barrel for the :class:`Identity` facade and related types.

The implementation lives in
:mod:`unique_toolkit.experimental.resources.facades.identity`; this package
re-exports the same public names for a shorter import path.
"""

from __future__ import annotations

from unique_toolkit.experimental.resources.facades.identity.service import Identity
from unique_toolkit.experimental.resources.group import (
    GroupDeleted,
    GroupInfo,
    GroupMember,
    GroupMembership,
    Groups,
    GroupWithConfiguration,
)
from unique_toolkit.experimental.resources.user import (
    UserGroupMembership,
    UserInfo,
    Users,
    UserWithConfiguration,
)

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
