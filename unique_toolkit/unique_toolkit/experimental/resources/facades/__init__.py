"""Facades over multiple :mod:`..` sibling resources.

A *facade* (GoF Facade pattern) is a resource-shaped object that owns no
SDK call signatures of its own and instead composes two or more sibling
resources behind a single ``(user_id, company_id)`` context. From the
caller's point of view it looks and constructs like any other resource —
``Identity(user_id=..., company_id=...)`` vs ``Users(user_id=...,
company_id=...)`` — but the CRUD surface is delegated to the composed
sub-services via attributes (e.g. ``identity.users.list(...)``,
``identity.groups.add_members(...)``).

The bucket exists instead of placing facades flat under :mod:`..` so that:

- readers can distinguish at a glance between primitives (one SDK resource)
  and aggregates (two or more SDK resources);
- the aggregating classes have a natural home to grow into when more than
  one facade exists (today: only :class:`~.identity.Identity`);
- the sibling resources they compose can be imported directly from
  :mod:`..` without the facade pulling them into a second graph.

A facade belongs in :mod:`..components` rather than here when it adds
behaviour beyond delegation (orchestration, derived views, caching,
parallel fan-out). If every method is a one-liner that forwards to a
sub-resource, it is a facade; otherwise it is a capability.

Planned contents:

* ``identity`` — :class:`Identity` over :mod:`..user` + :mod:`..group`.
"""
