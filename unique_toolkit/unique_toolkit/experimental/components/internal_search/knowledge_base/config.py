from __future__ import annotations

import json
import warnings
from typing import Annotated, Any, Self

from pydantic import (
    BeforeValidator,
    Field,
    field_serializer,
    model_validator,
)
from pydantic.json_schema import WithJsonSchema

from unique_toolkit._common.config_checker import register_config
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.pydantic_helpers import DeactivatedNone
from unique_toolkit.content.schemas import ContentRerankerConfig
from unique_toolkit.content.smart_rules import parse_uniqueql
from unique_toolkit.experimental.components.internal_search.base.config import (
    InternalSearchConfig,
)


def _parse_and_validate_uniqueql(v: Any) -> dict[str, Any] | None:
    if v is None:
        return None
    if isinstance(v, str):
        if v.strip() == "":
            return None
        try:
            v = json.loads(v)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e
    if isinstance(v, dict):
        parse_uniqueql(v)  # validates structure; discard model, keep raw dict
        return v
    raise ValueError(f"Expected JSON string or dict, got {type(v).__name__}")


UniqueQLDict = Annotated[
    dict[str, Any] | None,
    BeforeValidator(_parse_and_validate_uniqueql),
    WithJsonSchema(
        {
            "anyOf": [
                {"type": "string", "title": "UniqueQL (JSON)"},
                {"type": "null", "title": "Deactivated", "description": "None"},
            ]
        }
    ),
]


@register_config()
class KnowledgeBaseInternalSearchConfig(InternalSearchConfig):
    scope_ids: Annotated[
        Annotated[list[str], Field(title="Scope IDs")] | DeactivatedNone,
        RJSFMetaTag({"anyOf": [{"items": {"ui:title": "Scope ID"}}, {}]}),
    ] = Field(
        default=None,
        deprecated=True,
        description=(
            "Not accepted for new configs. Use ``metadata_filter`` with "
            "``folderId`` / operator ``in`` and the raw scope ID values instead. "
            "If set, a deprecation warning is emitted and values are folded into "
            "a ``folderId in [scope_ids]`` metadata filter at search time."
        ),
    )
    metadata_filter: Annotated[
        UniqueQLDict,
        # Put textarea attrs on the string branch (index 0) only, not at field level.
        # If set at field level, RJSF's MultiSchemaField applies ui:widget to every
        # anyOf branch during option iteration, which crashes on non-string branches.
        RJSFMetaTag(
            {
                "ui:options": {"customValidation": "uniqueql"},
                "anyOf": [
                    {
                        "ui:widget": "textarea",
                        "ui:placeholder": '{"operator": "equals", "value": "...", "path": ["fieldName"]}',
                        "ui:emptyValue": "",
                    },
                    {},
                ],
            }
        ),
    ] = Field(
        default=None,
        description=(
            "Static UniqueQL metadata filter applied to every KB search. "
            "Pass as a JSON string or a plain dict. "
            "Overridden by chat context filter or per-invocation state override."
        ),
    )
    reranker_config: (
        Annotated[ContentRerankerConfig, Field(title="Active")] | DeactivatedNone
    ) = Field(
        default=None,
        description=(
            "Server-side reranker applied during retrieval. "
            "Passed directly to the KB search API — distinct from the "
            "client-side chunk_relevancy_sort_config in PostProcessorConfig."
        ),
    )

    @field_serializer("metadata_filter")
    def _serialize_metadata_filter(self, value: dict[str, Any] | None) -> str | None:
        """Serialize back to a JSON string so the output matches the JSON schema (string | null)."""
        if value is None:
            return None
        return json.dumps(value)

    @model_validator(mode="after")
    def _warn_deprecated_scope_ids(self) -> Self:
        if self.scope_ids:
            warnings.warn(
                (
                    "KnowledgeBaseInternalSearchConfig.scope_ids is deprecated; "
                    "use metadata_filter with folderId operator 'in' instead."
                ),
                DeprecationWarning,
                stacklevel=5,  # Pydantic v2 model_validator adds ~3 frames above this validator
            )
        return self


__all__ = ["KnowledgeBaseInternalSearchConfig"]
