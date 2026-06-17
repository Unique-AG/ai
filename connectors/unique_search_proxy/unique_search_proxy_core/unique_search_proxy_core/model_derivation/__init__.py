"""Provider-agnostic Pydantic model derivation (config → request)."""

from unique_search_proxy_core.model_derivation.derive import derive_request_model
from unique_search_proxy_core.model_derivation.fields import (
    field_definition_from_info,
    plain_annotation,
    plain_annotation_for_llm,
    plain_annotation_for_non_strict_llm,
    plain_annotation_for_request,
    resolve_field_name,
)

__all__ = [
    "derive_request_model",
    "field_definition_from_info",
    "plain_annotation",
    "plain_annotation_for_llm",
    "plain_annotation_for_non_strict_llm",
    "plain_annotation_for_request",
    "resolve_field_name",
]
