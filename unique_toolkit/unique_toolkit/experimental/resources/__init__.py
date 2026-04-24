"""Typed adapters over ``unique_sdk``.

Thin wrappers around individual SDK resources that add little beyond
Pydantic schemas and sync/async function pairs. The canonical shape is::

    resources/<name>/
        functions.py   # free-standing sync + async calls
        schemas.py     # Pydantic models for request/response payloads
        service.py     # stateful, event-aware class over ``functions.py``

Resources are intentionally unopinionated: they do not own app bootstrap
concerns and do not add behavior beyond typing. Anything that does belongs
in :mod:`..capabilities`.

**Ergonomic call surfaces via** :func:`typing.overload`. Where the
underlying SDK endpoint accepts several mutually-exclusive identifier
shapes (``id`` vs ``email`` vs ``user_name``, ``user_id`` vs ``group_id``,
etc.), the service exposes a single method name backed by multiple
``@overload`` stubs — one per legal call shape — plus one runtime
implementation that dispatches at the bottom. This makes the permissible
calls discoverable at the type-checker / IDE completion layer instead of
buried in ``if kind == "email": ...`` logic that a caller has to reverse
engineer:

.. code-block:: python

    users.get(user_id="usr_abc")         # overload 1: by id
    users.get(email="alice@example.com") # overload 2: by email
    users.get(user_name="alice")         # overload 3: by username
    users.get(email=..., user_name=...)  # type error at call site

Resources that wrap a single-shape endpoint do not bother with overloads
and just type the parameters directly.

One sub-bucket lives here: :mod:`.facades`, for resource-shaped classes
that compose two or more sibling resources (currently only
:class:`~.facades.identity.Identity`). Facades share the same constructor
shape as a resource and are therefore filed under :mod:`.resources` rather
than as a peer folder.

Planned contents (current home → new home):

* ``chat``             ← :mod:`unique_toolkit.chat`
* ``content``          ← :mod:`unique_toolkit.content` (minus ``smart_rules``)
* ``embedding``        ← :mod:`unique_toolkit.embedding`
* ``language_model``   ← :mod:`unique_toolkit.language_model`
* ``short_term_memory``← :mod:`unique_toolkit.short_term_memory`
* ``elicitation``      ← :mod:`unique_toolkit.elicitation`
* ``agentic_table``    ← :mod:`unique_toolkit.agentic_table`
* ``user``             ← :mod:`unique_toolkit.experimental.identity` (user part)
* ``group``            ← :mod:`unique_toolkit.experimental.identity` (group part)
* ``content_folder``   ← :mod:`unique_toolkit.experimental.content_folder`
* ``scheduled_task``   ← :mod:`unique_toolkit.experimental.scheduled_task`
* ``facades.identity`` ← :mod:`unique_toolkit.experimental.identity`
  (the :class:`Identity` facade bundling the :class:`Users` and :class:`Groups` services)

One thing that *looks* like it should live here but does not:

* ``content_tree`` is a capability (see :mod:`..capabilities.content_tree`)
  — it does not wrap a ``unique_sdk`` endpoint, it composes the ``content``
  resource into a derived view (parallel pagination, scope-id resolution,
  trie rendering, fuzzy search).
"""
