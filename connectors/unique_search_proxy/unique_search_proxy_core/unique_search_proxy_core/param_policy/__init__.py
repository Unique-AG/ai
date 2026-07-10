"""Deployment field policies for optional provider knobs.

Public surface: :class:`ExposableParam` (the admin-side ``{expose, value}``
deployment value), :class:`ExposedParams` (the base class of LLM-facing
parameter models), and the shared leading-field names. Everything else callers
need lives as methods on the config base classes
(``BaseSearchEngineConfig.request_model()`` / ``exposed_params_model()`` /
``merge()`` / ``provider_query_params()``).
"""

from unique_search_proxy_core.param_policy.exposable_param import ExposableParam
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams

#: Required leading field of every search / agent-search request.
QUERY_FIELD = "query"
#: Required leading field of every crawl request.
URLS_FIELD = "urls"

__all__ = [
    "QUERY_FIELD",
    "URLS_FIELD",
    "ExposableParam",
    "ExposedParams",
]
