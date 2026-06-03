from __future__ import annotations

import importlib
from functools import lru_cache
from typing import Annotated, Any, Literal, Union, cast, get_args, get_origin

from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo

from unique_search_proxy.web.core.param_policy import QUERY_FIELD
from unique_search_proxy.web.core.param_policy.exposable_param import (
    exposable_param_inner_type,
    flatten_union_args,
    is_exposable_param_type,
)
from unique_search_proxy.web.core.schema import camelized_model_config


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
        field_name = _resolve_field_name(call_schema, exposed_name)
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
            resolved_annotation = _plain_annotation_for_llm(field_info.annotation)
        elif config_ann is not None:
            resolved_annotation = _plain_annotation_for_non_strict_llm(config_ann)
        else:
            resolved_annotation = None
        field_definitions[field_name] = _field_definition_from_info(
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
    field_definitions: dict[str, tuple[Any, Any]] = {
        QUERY_FIELD: (
            str,
            Field(
                ...,
                min_length=1,
                description="Search query string",
            ),
        ),
    }
    for field_name, field_info in config_cls.model_fields.items():
        plain_annotation = _plain_annotation_for_request(field_info.annotation)
        field_definitions[field_name] = _field_definition_from_info(
            field_info,
            annotation=plain_annotation,
            force_default_none=is_exposable_param_type(field_info.annotation),
        )

    model_config = config_cls.model_config or camelized_model_config
    request_model = create_model(
        f"{config_cls.__name__}Request",
        __config__=model_config,
        **cast(Any, field_definitions),
    )
    config_module = importlib.import_module(config_cls.__module__)
    request_model.model_rebuild(_types_namespace=dict(vars(config_module)))
    return request_model


def build_llm_call_model(
    config_cls: type[BaseModel],
    config: BaseModel,
    *,
    strict_required: bool = True,
) -> type[BaseModel]:
    """Derive LLM call-schema model from config instance (query + ``expose=True`` fields)."""
    from unique_search_proxy.web.core.search_engines.params import (
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


def _plain_annotation_for_request(annotation: Any) -> Any:
    """Unwrap ``ExposableParam[T]`` for ``POST /v1/search`` (optional when inner allows null)."""
    if is_exposable_param_type(annotation):
        inner = exposable_param_inner_type(annotation)
        union_args = flatten_union_args(inner)
        if type(None) in union_args:
            return inner
        return inner | None
    return _plain_annotation(annotation)


def _plain_annotation_for_non_strict_llm(config_field_annotation: Any) -> Any:
    """LLM call schema (non-strict): use config inner ``T`` without adding ``| None``."""
    if is_exposable_param_type(config_field_annotation):
        return exposable_param_inner_type(config_field_annotation)
    return _plain_annotation(config_field_annotation)


def _plain_annotation(annotation: Any) -> Any:
    """Unwrap unions and ``Annotated`` for plain derived types."""
    if is_exposable_param_type(annotation):
        return _plain_annotation_for_request(annotation)
    origin = get_origin(annotation)
    if origin is Literal:
        return annotation
    if origin is Annotated:
        args = get_args(annotation)
        if args:
            return _plain_annotation(args[0])

    union_args = flatten_union_args(annotation)
    if len(union_args) > 1:
        plain_members: list[Any] = []
        has_optional = False
        for arg in union_args:
            if arg is type(None):
                has_optional = True
                continue
            plain_members.append(_plain_annotation(arg))
        if len(plain_members) == 1:
            inner = plain_members[0]
            if has_optional:
                return inner | None
            return inner
        return Union[tuple(plain_members)]  # type: ignore[return-value]

    return annotation


def _plain_annotation_for_llm(annotation: Any) -> Any:
    """Required LLM fields: drop ``None`` from optional provider knob types."""
    plain = _plain_annotation(annotation)
    union_args = flatten_union_args(plain)
    if type(None) not in union_args:
        return plain
    members = [arg for arg in union_args if arg is not type(None)]
    if len(members) == 1:
        return members[0]
    if members:
        return Union[tuple(members)]  # type: ignore[return-value]
    return plain


def _resolve_field_name(call_schema: type[BaseModel], exposed_name: str) -> str:
    if exposed_name in call_schema.model_fields:
        return exposed_name

    for field_name, field_info in call_schema.model_fields.items():
        if field_info.alias == exposed_name:
            return field_name
        if field_info.serialization_alias == exposed_name:
            return field_name

    raise ValueError(
        f"Field {exposed_name!r} is not defined on {call_schema.__name__}",
    )


def _field_definition_from_info(
    field_info: FieldInfo,
    *,
    annotation: Any | None = None,
    force_default_none: bool = False,
    strict_required: bool = False,
    default_override: Any | None = None,
    use_default_override: bool = False,
) -> tuple[Any, Any]:
    resolved_annotation = (
        annotation if annotation is not None else field_info.annotation
    )
    field_kwargs: dict[str, Any] = {
        "description": field_info.description,
        "json_schema_extra": field_info.json_schema_extra,
    }
    if field_info.title is not None:
        field_kwargs["title"] = field_info.title
    if field_info.alias is not None:
        field_kwargs["alias"] = field_info.alias
    if field_info.serialization_alias is not None:
        field_kwargs["serialization_alias"] = field_info.serialization_alias
    for constraint in ("ge", "le", "gt", "lt", "min_length", "max_length"):
        value = getattr(field_info, constraint, None)
        if value is not None:
            field_kwargs[constraint] = value

    if strict_required or field_info.is_required():
        return (
            resolved_annotation,
            Field(..., **field_kwargs),
        )

    if use_default_override:
        default = default_override
    elif force_default_none:
        default = None
    else:
        default = field_info.get_default(call_default_factory=True)
    return (
        resolved_annotation,
        Field(default=default, **field_kwargs),
    )
