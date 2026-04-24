"""Adapters for third-party frameworks.

Renamed from ``framework_utilities`` to reflect that these subpackages are
integrations with external libraries, not general-purpose utilities.

Planned contents (current home → new home):

* ``openai``    ← :mod:`unique_toolkit.framework_utilities.openai`
* ``langchain`` ← :mod:`unique_toolkit.framework_utilities.langchain`
  (remains an optional dependency, surfaced via a conditional re-export in
  the top-level ``__init__``)
"""
