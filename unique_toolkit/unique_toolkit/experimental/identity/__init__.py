"""``unique_toolkit.experimental.identity`` — user and group directory management.

.. warning::

    **Experimental.** This subpackage is exposed under
    :mod:`unique_toolkit.experimental` and its public API may change without
    notice. It is not covered by the toolkit's normal stability guarantees.

A thin, Linux-inspired wrapper around :mod:`unique_sdk.User` and
:mod:`unique_sdk.Group`. The single entry point is :class:`Identity`; the
subpackage also exposes the Pydantic schemas used on responses.
"""

from unique_toolkit.experimental.identity.schemas import (
    GroupDeleted as GroupDeleted,
)
from unique_toolkit.experimental.identity.schemas import (
    GroupInfo as GroupInfo,
)
from unique_toolkit.experimental.identity.schemas import (
    GroupMember as GroupMember,
)
from unique_toolkit.experimental.identity.schemas import (
    GroupMembership as GroupMembership,
)
from unique_toolkit.experimental.identity.schemas import (
    GroupWithConfiguration as GroupWithConfiguration,
)
from unique_toolkit.experimental.identity.schemas import (
    UserGroupMembership as UserGroupMembership,
)
from unique_toolkit.experimental.identity.schemas import (
    UserInfo as UserInfo,
)
from unique_toolkit.experimental.identity.schemas import (
    UserWithConfiguration as UserWithConfiguration,
)
from unique_toolkit.experimental.identity.service import Identity as Identity

__all__ = [
    "GroupDeleted",
    "GroupInfo",
    "GroupMember",
    "GroupMembership",
    "GroupWithConfiguration",
    "Identity",
    "UserGroupMembership",
    "UserInfo",
    "UserWithConfiguration",
]
