from __future__ import annotations

from functools import lru_cache
from typing import Any, cast

from pydantic import BaseModel, Field, create_model

from unique_search_proxy_core.model_derivation import (
    derive_request_model,
    field_definition_from_info,
    plain_annotation_for_llm,
    plain_annotation_for_non_strict_llm,
    resolve_field_name,
)
from unique_search_proxy_core.param_policy import QUERY_FIELD
from unique_search_proxy_core.schema import camelized_model_config


def _search_request_model_name(config_cls: type[BaseModel]) -> str:
    """``GoogleConfig`` -> ``GoogleSearchRequest``."""
    base = config_cls.__name__
    if base.endswith("Config"):
        base = base[: -len("Config")]
    return f"{base}SearchRequest"


def project_call_schema(
    call_schema: type[BaseModel],
    exposed_fields: list[str],
    *,
    model_name_suffix: str = "LlmProjection",
    strict_required: bool = False,
    field_defaults: dict[str, Any] | None = None,
    config_field_annotations: dict[str, Any] | None = None,
) -> type[BaseModel]:
    """Project a call schema down to the fields exposed to LLM-driven callers."""
    if not exposed_fields:
        raise ValueError("exposed_fields must contain at least one field name")

    field_definitions: dict[str, tuple[Any, Any]] = {}
    for exposed_name in exposed_fields:
        field_name = resolve_field_name(call_schema, exposed_name)
        field_info = call_schema.model_fields[field_name]
        default_override = (
            field_defaults.get(field_name) if field_defaults is not None else None
        )
        has_default_override = (
            field_defaults is not None and field_name in field_defaults
        )
        config_ann = (
            config_field_annotations.get(field_name)
            if config_field_annotations is not None
            else None
        )
        if strict_required:
            resolved_annotation = plain_annotation_for_llm(field_info.annotation)
        elif config_ann is not None:
            resolved_annotation = plain_annotation_for_non_strict_llm(config_ann)
        else:
            resolved_annotation = None
        field_definitions[field_name] = field_definition_from_info(
            field_info,
            annotation=resolved_annotation,
            strict_required=strict_required,
            default_override=default_override if has_default_override else None,
            use_default_override=has_default_override,
        )

    model_config = call_schema.model_config or camelized_model_config
    return create_model(
        f"{call_schema.__name__}{model_name_suffix}",
        __config__=model_config,
        **cast(Any, field_definitions),
    )


def project_json_schema(
    call_schema: type[BaseModel],
    exposed_fields: list[str],
) -> dict[str, Any]:
    """Return the JSON schema for the LLM-facing projection of a call schema."""
    projected = project_call_schema(call_schema, exposed_fields)
    return projected.model_json_schema()


@lru_cache(maxsize=32)
def build_request_model(config_cls: type[BaseModel]) -> type[BaseModel]:
    """Derive ``POST /v1/search`` body: ``query`` + all config fields as plain types."""
    return derive_request_model(
        config_cls,
        leading_fields=(
            (
                QUERY_FIELD,
                (
                    str,
                    Field(
                        ...,
                        min_length=1,
                        description="Search query string",
                    ),
                ),
            ),
        ),
        model_name=_search_request_model_name,
        unwrap_exposable_params=True,
    )


def build_llm_call_model(
    config_cls: type[BaseModel],
    config: BaseModel,
    *,
    strict_required: bool = True,
) -> type[BaseModel]:
    """Derive LLM call-schema model from config instance (query + ``expose=True`` fields)."""
    from unique_search_proxy_core.search_engines.params import (
        config_defaults,
        llm_exposed_field_names,
    )

    request_model = build_request_model(config_cls)
    exposed = llm_exposed_field_names(config)
    merge_defaults = None if strict_required else config_defaults(config)
    config_annotations = {
        name: info.annotation for name, info in config_cls.model_fields.items()
    }
    return project_call_schema(
        request_model,
        exposed,
        strict_required=strict_required,
        field_defaults=merge_defaults,
        config_field_annotations=config_annotations,
    )
