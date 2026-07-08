"""LLM-facing call JSON Schema derived from deployment config (no HTTP)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, create_model

from unique_search_proxy_core.param_policy.annotations import (
    plain_annotation_for_tool_field,
    resolve_field_name,
)
from unique_search_proxy_core.param_policy.resolver import (
    ConfigRequestResolver,
    project_call_schema,
)
from unique_search_proxy_core.providers.schema import provider_default_config
from unique_search_proxy_core.search_engines.base import (
    SearchEngineType,
    get_search_engine_mode,
)
from unique_search_proxy_core.search_engines.config_types import (
    ENGINE_NAME_TO_CONFIG,
    SearchEngineConfigTypes,
    parse_search_engine_config,
)


@dataclass(frozen=True)
class SearchCallSchemaDescriptor:
    """Metadata and JSON Schema for the engine call model on ``POST /v1/search``."""

    engine: str
    mode: str
    call_schema: dict[str, Any]


def resolve_search_call_schema_from_config(
    engine_id: str,
    config: SearchEngineConfigTypes,
    *,
    strict: bool = True,
) -> SearchCallSchemaDescriptor:
    """Project the LLM-visible call surface from a parsed deployment config."""
    engine_type = SearchEngineType(engine_id.lower())
    config_cls = ENGINE_NAME_TO_CONFIG[engine_type.value]
    if type(config) is not config_cls:
        raise ValueError(
            f"Config type {type(config).__name__} does not match engine {engine_id!r}",
        )

    projected = ConfigRequestResolver.call_schema(config, strict=strict)
    return SearchCallSchemaDescriptor(
        engine=engine_type.value,
        mode=get_search_engine_mode(engine_type).value,
        call_schema=projected.model_json_schema(),
    )


def resolve_search_call_schema(
    engine_id: str,
    *,
    config: SearchEngineConfigTypes | dict[str, Any] | None = None,
    strict: bool = True,
) -> SearchCallSchemaDescriptor:
    """Resolve call schema from deployment config or engine defaults."""
    if config is not None:
        parsed = (
            config
            if isinstance(config, BaseModel)
            else parse_search_engine_config(config)
        )
        return resolve_search_call_schema_from_config(engine_id, parsed, strict=strict)

    defaults = provider_default_config("search_engine", engine_id)
    parsed = parse_search_engine_config(defaults)
    return resolve_search_call_schema_from_config(engine_id, parsed, strict=strict)


def build_exposed_params_model(config: BaseModel) -> type[BaseModel] | None:
    """Derive an optional-field model of LLM-exposed engine params (excluding ``query``).

    Returns ``None`` when no engine parameters are marked ``expose=True``.
    """
    exposed = ConfigRequestResolver.exposed_field_names(config, with_query=False)
    if not exposed:
        return None

    config_cls = type(config)
    request_model = ConfigRequestResolver.request_model(config_cls)
    config_annotations = {
        name: info.annotation for name, info in config_cls.model_fields.items()
    }
    return project_call_schema(
        request_model,
        exposed,
        model_name_suffix="ExposedParams",
        strict_required=False,
        field_defaults=ConfigRequestResolver.resolve_values(config),
        config_field_annotations=config_annotations,
    )


def exposed_field_names(config: BaseModel) -> list[str]:
    """Python field names exposed to LLM callers (``query`` excluded)."""
    return ConfigRequestResolver.exposed_field_names(config, with_query=False)


def build_exposed_tool_field_defs(
    config: BaseModel,
) -> dict[str, tuple[Any, Any]] | None:
    """Flat ``create_model`` field defs for tool schemas (description-only, optional).

    Admin defaults are not embedded in the tool schema; they are merged at search time.
    """
    exposed = exposed_field_names(config)
    if not exposed:
        return None

    config_cls = type(config)
    request_model = ConfigRequestResolver.request_model(config_cls)
    field_defs: dict[str, tuple[Any, Any]] = {}
    for exposed_name in exposed:
        field_name = resolve_field_name(request_model, exposed_name)
        config_field_info = config_cls.model_fields.get(field_name)
        if config_field_info is None:
            for cfg_name, cfg_info in config_cls.model_fields.items():
                if cfg_info.alias == exposed_name:
                    config_field_info = cfg_info
                    field_name = cfg_name
                    break
        description = (
            config_field_info.description
            if config_field_info is not None
            else field_name
        )
        annotation = plain_annotation_for_tool_field(
            config_field_info.annotation
            if config_field_info is not None
            else request_model.model_fields[field_name].annotation
        )
        union_args = getattr(annotation, "__args__", None)
        if union_args and type(None) in union_args:
            optional_annotation = annotation
        else:
            optional_annotation = annotation | None
        field_defs[field_name] = (
            optional_annotation,
            Field(default=None, description=description),
        )
    return field_defs


def build_exposed_tool_fields_model(config: BaseModel) -> type[BaseModel] | None:
    """Pydantic model of flat exposed tool fields (for schema emission / tests)."""
    field_defs = build_exposed_tool_field_defs(config)
    if field_defs is None:
        return None
    return create_model(
        f"{type(config).__name__}ExposedToolFields",
        __config__=ConfigDict(extra="forbid"),
        **cast(Any, field_defs),
    )


def strip_exposed_tool_schema_noise(
    schema: dict[str, Any],
    *,
    field_names: list[str],
) -> dict[str, Any]:
    """Remove ``title`` and ``default`` from exposed property nodes in a JSON schema."""
    field_name_set = set(field_names)
    return _strip_exposed_tool_schema_node(schema, field_name_set)


def _strip_exposed_tool_schema_node(
    node: dict[str, Any],
    field_names: set[str],
) -> dict[str, Any]:
    out = dict(node)
    properties = out.get("properties")
    if isinstance(properties, dict):
        cleaned_properties: dict[str, Any] = {}
        for key, value in properties.items():
            if isinstance(value, dict):
                cleaned = _strip_exposed_tool_schema_node(value, field_names)
                if key in field_names:
                    cleaned.pop("title", None)
                    cleaned.pop("default", None)
                cleaned_properties[key] = cleaned
            else:
                cleaned_properties[key] = value
        out["properties"] = cleaned_properties

    for combiner in ("anyOf", "oneOf", "allOf"):
        variants = out.get(combiner)
        if isinstance(variants, list):
            out[combiner] = [
                _strip_exposed_tool_schema_node(variant, field_names)
                if isinstance(variant, dict)
                else variant
                for variant in variants
            ]

    items = out.get("items")
    if isinstance(items, dict):
        out["items"] = _strip_exposed_tool_schema_node(items, field_names)

    defs = out.get("$defs")
    if isinstance(defs, dict):
        out["$defs"] = {
            name: _strip_exposed_tool_schema_node(defn, field_names)
            if isinstance(defn, dict)
            else defn
            for name, defn in defs.items()
        }

    return out


def exposed_tool_fields_json_schema(config: BaseModel) -> dict[str, Any]:
    """JSON schema for flat exposed tool fields with provider noise stripped."""
    model = build_exposed_tool_fields_model(config)
    if model is None:
        raise ValueError("No exposed tool fields on config")
    return strip_exposed_tool_schema_noise(
        model.model_json_schema(),
        field_names=exposed_field_names(config),
    )


__all__ = [
    "SearchCallSchemaDescriptor",
    "build_exposed_params_model",
    "build_exposed_tool_field_defs",
    "build_exposed_tool_fields_model",
    "exposed_field_names",
    "exposed_tool_fields_json_schema",
    "resolve_search_call_schema",
    "resolve_search_call_schema_from_config",
    "strip_exposed_tool_schema_noise",
]
