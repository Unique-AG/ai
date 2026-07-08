"""Annotation/field plumbing for deriving models from ``ExposableParam`` configs.

These helpers translate a deployment-config field annotation into the plain
annotation used by each derived surface (HTTP request body, LLM call schema,
tool JSON schema) and rebuild a matching ``FieldInfo``. They are the low-level
companion to :class:`~unique_search_proxy_core.param_policy.resolver.ConfigRequestResolver`.

Typing note: a Python type annotation is not expressible as one static type — it
may be a class, a union, ``Annotated[...]``, ``Literal[...]`` or a parametrized
generic alias. ``Annotation`` is an ``Any`` alias that documents "this value is a
type annotation" at every boundary that traffics in them.
"""

from __future__ import annotations

from functools import reduce
from operator import or_
from typing import Annotated, Any, Literal, TypeAlias, get_args, get_origin

from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo

from unique_search_proxy_core.param_policy.exposable_param import (
    exposable_param_inner_type,
    flatten_union_args,
    is_exposable_param_type,
)

#: A Python type annotation object (see module docstring).
Annotation: TypeAlias = Any

#: A ``create_model`` field spec: ``(annotation, FieldInfo)``.
FieldDefinition: TypeAlias = tuple[Annotation, FieldInfo]

_COLLECTION_ORIGINS: tuple[type, ...] = (dict, list, tuple, set, frozenset)


def _union_of(members: list[Annotation]) -> Annotation:
    """Combine annotations with ``|`` (``[int, str]`` -> ``int | str``)."""
    return reduce(or_, members)


def plain_annotation_for_request(annotation: Annotation) -> Annotation:
    """Unwrap ``ExposableParam[T]`` for HTTP request bodies (optional when inner allows null)."""
    if is_exposable_param_type(annotation):
        inner = exposable_param_inner_type(annotation)
        union_args = flatten_union_args(inner)
        if type(None) in union_args:
            return inner
        return inner | None
    return _plain_annotation(annotation)


def plain_annotation_for_non_strict_llm(
    config_field_annotation: Annotation,
) -> Annotation:
    """LLM call schema (non-strict): use config inner ``T`` without adding ``| None``."""
    if is_exposable_param_type(config_field_annotation):
        return exposable_param_inner_type(config_field_annotation)
    return _plain_annotation(config_field_annotation)


def plain_annotation_for_llm(annotation: Annotation) -> Annotation:
    """Required LLM fields: drop ``None`` from optional provider knob types."""
    plain = _plain_annotation(annotation)
    union_args = flatten_union_args(plain)
    if type(None) not in union_args:
        return plain
    members = [arg for arg in union_args if arg is not type(None)]
    if len(members) == 1:
        return members[0]
    if members:
        return _union_of(members)
    return plain


def plain_annotation_for_tool_field(config_field_annotation: Annotation) -> Annotation:
    """Tool JSON schema: plain value types without admin/RSJF metadata or ``DeactivatedNone``."""
    if is_exposable_param_type(config_field_annotation):
        inner = exposable_param_inner_type(config_field_annotation)
    else:
        inner = config_field_annotation

    union_args = flatten_union_args(inner)
    if len(union_args) > 1:
        members = [
            _strip_annotated_field_metadata(arg)
            for arg in union_args
            if arg is not type(None) and not _is_deactivated_none_annotation(arg)
        ]
        if not members:
            return type(None)
        return _union_of(members)

    return _strip_annotated_field_metadata(inner)


def resolve_field_name(call_schema: type[BaseModel], exposed_name: str) -> str:
    """Map an exposed (possibly aliased) name to the model's Python field name."""
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
    annotation: Annotation | None = None,
    force_default_none: bool = False,
    strict_required: bool = False,
    default_override: Any = None,
    use_default_override: bool = False,
) -> FieldDefinition:
    """Rebuild a ``(annotation, FieldInfo)`` pair, carrying over metadata/constraints."""
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
        return (resolved_annotation, Field(..., **field_kwargs))

    if use_default_override:
        default = default_override
    elif force_default_none:
        default = None
    else:
        default = field_info.get_default(call_default_factory=True)
    return (resolved_annotation, Field(default=default, **field_kwargs))


def _plain_annotation(annotation: Annotation) -> Annotation:
    """Unwrap unions and ``Annotated`` for plain derived types."""
    if is_exposable_param_type(annotation):
        return plain_annotation_for_request(annotation)
    origin = get_origin(annotation)
    if origin is Literal:
        return annotation
    if origin is Annotated:
        args = get_args(annotation)
        if args:
            return _plain_annotation(args[0])

    if origin in _COLLECTION_ORIGINS:
        args = get_args(annotation)
        if args:
            plain_args = tuple(_plain_annotation(arg) for arg in args)
            return origin[plain_args]
        return annotation

    union_args = flatten_union_args(annotation)
    if len(union_args) > 1:
        plain_members: list[Annotation] = []
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
        return _union_of(plain_members)

    return annotation


def _is_deactivated_none_annotation(annotation: Annotation) -> bool:
    """True for ``Annotated[None, Field(title="Deactivated", ...)]`` provider sentinels."""
    if get_origin(annotation) is Annotated:
        args = get_args(annotation)
        return bool(args) and args[0] is type(None)
    return False


def _strip_annotated_field_metadata(annotation: Annotation) -> Annotation:
    """Drop ``Annotated[..., Field(title=...)]`` wrappers; keep ``Literal`` and containers."""
    origin = get_origin(annotation)
    if origin is Literal:
        return annotation
    if origin is Annotated:
        args = get_args(annotation)
        if args:
            return _strip_annotated_field_metadata(args[0])
    if origin in _COLLECTION_ORIGINS:
        args = get_args(annotation)
        if args:
            plain_args = tuple(_strip_annotated_field_metadata(arg) for arg in args)
            return origin[plain_args]
        return annotation
    return annotation
