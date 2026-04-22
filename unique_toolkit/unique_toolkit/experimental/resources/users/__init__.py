"""Typed wrapper over the ``unique_sdk`` user resource.

Carved out of the current monolithic ``identity/`` package. Only the
user-centric pieces live here:

* ``Users`` service (from ``identity/service.py``)
* functions: ``list_users``, ``get_user_by_id``, ``find_user``,
  ``get_user_groups``, ``update_user_configuration``
  (+ their ``_async`` siblings, from ``identity/functions.py``)
* schemas: ``UserInfo``, ``UserWithConfiguration``, ``UserGroupMembership``
  (from ``identity/schemas.py``)

The cross-cutting ``Users.groups_of`` / ``Users.is_member`` relational
helpers stay on this resource because the SDK's "groups of user" endpoint
hangs off the user entity. The :class:`Identity` facade that composes
``Users`` + ``Groups`` lives in :mod:`..clients.identity`.
"""
