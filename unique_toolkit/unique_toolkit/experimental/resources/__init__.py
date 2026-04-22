"""Typed adapters over ``unique_sdk``.

Thin wrappers around individual SDK resources that add little beyond
Pydantic schemas and sync/async function pairs. The canonical shape is::

    resources/<name>/
        functions.py   # free-standing sync + async calls
        schemas.py     # Pydantic models for request/response payloads
        service.py     # stateful, event-aware class over ``functions.py``

Resources are intentionally unopinionated: they do not compose each other,
do not own app bootstrap concerns, and do not add behavior beyond typing.
Anything that does belongs in :mod:`..capabilities` or :mod:`..clients`.

Planned contents (current home → new home):

* ``chat``             ← :mod:`unique_toolkit.chat`
* ``content``          ← :mod:`unique_toolkit.content` (minus ``smart_rules``)
* ``embedding``        ← :mod:`unique_toolkit.embedding`
* ``language_model``   ← :mod:`unique_toolkit.language_model`
* ``short_term_memory``← :mod:`unique_toolkit.short_term_memory`
* ``elicitation``      ← :mod:`unique_toolkit.elicitation`
* ``agentic_table``    ← :mod:`unique_toolkit.agentic_table`
* ``users``            ← :mod:`unique_toolkit.experimental.identity` (user part)
* ``groups``           ← :mod:`unique_toolkit.experimental.identity` (group part)
* ``content_folder``   ← :mod:`unique_toolkit.experimental.content_folder`
* ``scheduled_task``   ← :mod:`unique_toolkit.experimental.scheduled_task`

Two things that *look* like they should live here but do not:

* ``identity`` is a facade (see :mod:`..clients.identity`), not a
  resource — it bundles :mod:`.users` + :mod:`.groups`.
* ``content_tree`` is a capability (see :mod:`..capabilities.content_tree`)
  — it does not wrap a ``unique_sdk`` endpoint, it composes the ``content``
  resource into a derived view (parallel pagination, scope-id resolution,
  trie rendering, fuzzy search).
"""
