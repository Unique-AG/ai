"""``unique_toolkit.experimental.clients.identity`` — the :class:`Identity` facade.

.. warning::

    **Experimental.** This subpackage is exposed under
    :mod:`unique_toolkit.experimental` and its public API may change without
    notice. It is not covered by the toolkit's normal stability guarantees.

:class:`Identity` is the one-stop facade that bundles both directory
resources behind a single ``(user_id, company_id)`` object:

- :attr:`Identity.users` → :class:`~unique_toolkit.experimental.resources.users.Users`
- :attr:`Identity.groups` → :class:`~unique_toolkit.experimental.resources.groups.Groups`

For convenience, the :class:`Users` and :class:`Groups` services together
with their Pydantic response schemas (:class:`UserInfo`, :class:`GroupInfo`,
...) are re-exported here. The actual implementations live in
:mod:`unique_toolkit.experimental.resources.users` and
:mod:`unique_toolkit.experimental.resources.groups`; import from there when
you only need a single resource.
"""

from unique_toolkit.experimental.clients.identity.service import Identity
from unique_toolkit.experimental.resources.groups import (
    GroupDeleted,
    GroupInfo,
    GroupMember,
    GroupMembership,
    Groups,
    GroupWithConfiguration,
)
from unique_toolkit.experimental.resources.users import (
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
