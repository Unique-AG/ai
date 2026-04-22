"""Facades that compose multiple :mod:`..resources` into a single object.

These are the ergonomic entry points most users import. A client may also
mix in behavior from :mod:`..capabilities` but must not own SDK call
signatures directly — those belong in resources.

Planned contents (current home → new home):

* ``chat_service``    ← :mod:`unique_toolkit.services.chat_service`
* ``knowledge_base``  ← :mod:`unique_toolkit.services.knowledge_base`
  (wraps ``content`` + ``content_folder`` + ``content_tree``)
* ``identity``        ← :mod:`unique_toolkit.experimental.identity` (the
  ``Identity`` facade, once ``Users`` / ``Groups`` are carved out into
  :mod:`..resources.users` and :mod:`..resources.groups`)
* ``factory``         ← :mod:`unique_toolkit.services.factory`
"""
