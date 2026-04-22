"""Typed wrapper over the ``unique_sdk`` group resource.

Carved out of the current monolithic ``identity/`` package. Only the
group-centric pieces live here:

* ``Groups`` service (from ``identity/service.py``)
* functions: ``list_groups``, ``create_group``, ``delete_group``,
  ``rename_group``, ``update_group_configuration``, ``add_group_members``,
  ``remove_group_members`` (+ their ``_async`` siblings, from
  ``identity/functions.py``)
* schemas: ``GroupInfo``, ``GroupWithConfiguration``, ``GroupMember``,
  ``GroupMembership``, ``GroupDeleted`` (from ``identity/schemas.py``)

The :class:`Identity` facade that composes ``Users`` + ``Groups`` lives in
:mod:`..clients.identity`.
"""
