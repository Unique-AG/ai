from __future__ import annotations

from typing import Annotated, Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo

from unique_search_proxy_core.param_policy.exposable_param import (
    exposable_param_inner_type,
    flatten_union_args,
    is_exposable_param_type,
)

_COLLECTION_ORIGINS = (dict, list, tuple, set, frozenset)


def plain_annotation_for_request(annotation: Any) -> Any:
    """Unwrap ``ExposableParam[T]`` for HTTP request bodies (optional when inner allows null)."""
    if is_exposable_param_type(annotation):
        inner = exposable_param_inner_type(annotation)
        union_args = flatten_union_args(inner)
        if type(None) in union_args:
            return inner
        return inner | None
    return plain_annotation(annotation)


def plain_annotation_for_non_strict_llm(config_field_annotation: Any) -> Any:
    """LLM call schema (non-strict): use config inner ``T`` without adding ``| None``."""
    if is_exposable_param_type(config_field_annotation):
        return exposable_param_inner_type(config_field_annotation)
    return plain_annotation(config_field_annotation)


def plain_annotation(annotation: Any) -> Any:
    """Unwrap unions and ``Annotated`` for plain derived types."""
    if is_exposable_param_type(annotation):
        return plain_annotation_for_request(annotation)
    origin = get_origin(annotation)
    if origin is Literal:
        return annotation
    if origin is Annotated:
        args = get_args(annotation)
        if args:
            return plain_annotation(args[0])

    if origin in _COLLECTION_ORIGINS:
        args = get_args(annotation)
        if args:
            plain_args = tuple(plain_annotation(arg) for arg in args)
            return origin[plain_args]  # type: ignore[index]
        return annotation

    union_args = flatten_union_args(annotation)
    if len(union_args) > 1:
        plain_members: list[Any] = []
        has_optional = False
        for arg in union_args:
            if arg is type(None):
                has_optional = True
                continue
            plain_members.append(plain_annotation(arg))
        if len(plain_members) == 1:
            inner = plain_members[0]
            if has_optional:
                return inner | None
            return inner
        return Union[tuple(plain_members)]  # type: ignore[return-value]

    return annotation


def plain_annotation_for_llm(annotation: Any) -> Any:
    """Required LLM fields: drop ``None`` from optional provider knob types."""
    plain = plain_annotation(annotation)
    union_args = flatten_union_args(plain)
    if type(None) not in union_args:
        return plain
    members = [arg for arg in union_args if arg is not type(None)]
    if len(members) == 1:
        return members[0]
    if members:
        return Union[tuple(members)]  # type: ignore[return-value]
    return plain


def resolve_field_name(call_schema: type[BaseModel], exposed_name: str) -> str:
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


def field_definition_from_info(
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
