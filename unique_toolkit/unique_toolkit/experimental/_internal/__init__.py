"""Package-private primitives — not part of the public API.

Replaces the current :mod:`unique_toolkit._common` junk drawer. Modules
here are implementation details; anything users are expected to import must
be promoted into :mod:`..resources`, :mod:`..capabilities`, or
:mod:`..integrations` first.

Planned contents (current home → new home):

* ``http``     ← :mod:`unique_toolkit._common.endpoint_builder`,
  :mod:`unique_toolkit._common.endpoint_requestor`,
  :mod:`unique_toolkit._common.api_calling`
* ``pydantic`` ← :mod:`unique_toolkit._common.pydantic`,
  :mod:`unique_toolkit._common.pydantic_helpers`,
  :mod:`unique_toolkit._common.validators`,
  :mod:`unique_toolkit._common.base_model_type_attribute`
* ``utils``    ← :mod:`unique_toolkit._common.utils` plus the loose
  modules in :mod:`unique_toolkit._common` (``_time_utils``,
  ``string_utilities``, ``execution``, ``exception``, ``event_bus``,
  ``referencing``, ``validate_required_values``, ``_base_service``)
"""
