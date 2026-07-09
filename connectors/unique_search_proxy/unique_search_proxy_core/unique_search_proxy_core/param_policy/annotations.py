"""Annotation plumbing for deriving models from ``ExposableParam`` configs.

Every derived surface (HTTP request body, LLM call schema, tool JSON schema) is a
projection of the same config field. The three primitives here are all any
surface needs:

- :func:`plain_inner_type` — the single unwrap: strip ``ExposableParam``,
  ``Annotated`` metadata and ``DeactivatedNone`` sentinels down to the plain
  value type, preserving an explicit ``| None`` and keeping ``Literal`` /
  collection element types intact.
- :func:`as_optional` / :func:`as_required` — the only two optionality
  adjustments the surfaces differ by.

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
    ExposableParam,
    flatten_union_args,
    pydantic_parametrized_args,
)

#: A Python type annotation object (see module docstring).
Annotation: TypeAlias = Any

#: A ``create_model`` field spec: ``(annotation, FieldInfo)``.
FieldDefinition: TypeAlias = tuple[Annotation, FieldInfo]

_COLLECTION_ORIGINS: tuple[type, ...] = (dict, list, tuple, set, frozenset)


def _union_of(members: list[Annotation]) -> Annotation:
    """Combine annotations with ``|`` (``[int, str]`` -> ``int | str``)."""
    return reduce(or_, members)


def _exposable_inner(annotation: Annotation) -> Annotation:
    """Return the ``T`` of an ``ExposableParam[T]`` wrapper (``str`` when bare)."""
    args = pydantic_parametrized_args(annotation)
    if args:
        return args[0]
    origin = get_origin(annotation)
    if origin is ExposableParam:
        type_args = get_args(annotation)
        return type_args[0] if type_args else str
    if annotation is ExposableParam:
        return str
    return annotation


def _normalize(annotation: Annotation) -> Annotation:
    """Strip ``Annotated`` metadata and normalize ``DeactivatedNone`` to ``None``.

    Unions are rebuilt preserving an explicit ``| None``; ``Literal`` and
    collection element types are kept, so the plain value type survives intact.
    """
    origin = get_origin(annotation)
    if origin is Literal:
        return annotation
    if origin is Annotated:
        args = get_args(annotation)
        return _normalize(args[0]) if args else annotation
    if origin in _COLLECTION_ORIGINS:
        args = get_args(annotation)
        if args:
            return origin[tuple(_normalize(arg) for arg in args)]
        return annotation

    union_args = flatten_union_args(annotation)
    if len(union_args) > 1:
        members: list[Annotation] = []
        has_none = False
        for arg in union_args:
            normalized = _normalize(arg)
            if normalized is type(None):
                has_none = True
                continue
            members.append(normalized)
        if not members:
            return type(None)
        result = members[0] if len(members) == 1 else _union_of(members)
        return result | None if has_none else result
    return annotation


def plain_inner_type(annotation: Annotation) -> Annotation:
    """Unwrap ``ExposableParam``/``Annotated``/``DeactivatedNone`` to the plain type."""
    return _normalize(_exposable_inner(annotation))


def as_optional(annotation: Annotation) -> Annotation:
    """Ensure the annotation admits ``None`` (idempotent when already optional)."""
    if type(None) in flatten_union_args(annotation):
        return annotation
    return annotation | None


def as_required(annotation: Annotation) -> Annotation:
    """Drop ``None`` from an optional annotation (identity when already required)."""
    union_args = flatten_union_args(annotation)
    if type(None) not in union_args:
        return annotation
    members = [arg for arg in union_args if arg is not type(None)]
    if not members:
        return annotation
    return members[0] if len(members) == 1 else _union_of(members)


def resolve_field_name(model: type[BaseModel], exposed_name: str) -> str:
    """Map an exposed (possibly aliased) name to the model's Python field name."""
    if exposed_name in model.model_fields:
        return exposed_name

    for field_name, field_info in model.model_fields.items():
        if field_info.alias == exposed_name:
            return field_name
        if field_info.serialization_alias == exposed_name:
            return field_name

    raise ValueError(
        f"Field {exposed_name!r} is not defined on {model.__name__}",
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
