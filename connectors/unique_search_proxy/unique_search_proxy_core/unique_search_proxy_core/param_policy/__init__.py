"""Deployment field policies: ``ExposableParam`` for optional provider knobs."""

from unique_search_proxy_core.param_policy.exposable_param import (
    ExposableParam,
    exposable_param_inner_type,
    flatten_union_args,
    is_exposable_param_field,
    is_exposable_param_type,
    unwrap_exposable_param_value,
)

#: Canonical name of the required search/agent query field.
QUERY_FIELD = "query"

#: Canonical name of the required crawl ``urls`` field.
URLS_FIELD = "urls"

__all__ = [
    "QUERY_FIELD",
    "URLS_FIELD",
    "ExposableParam",
    "exposable_param_inner_type",
    "flatten_union_args",
    "is_exposable_param_field",
    "is_exposable_param_type",
    "unwrap_exposable_param_value",
]
