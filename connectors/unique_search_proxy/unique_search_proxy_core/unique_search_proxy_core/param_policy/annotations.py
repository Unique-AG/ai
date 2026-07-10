"""Annotation plumbing for deriving models from ``ExposableParam`` configs.

Both derived surfaces (HTTP request body, exposed-params model) are projections
of the same config fields. The primitives here are all they need:

- :func:`plain_inner_type` — the single unwrap: strip ``ExposableParam``,
  ``Annotated`` metadata and ``DeactivatedNone`` sentinels down to the plain
  value type, preserving an explicit ``| None`` and keeping ``Literal`` /
  collection element types intact.
- :func:`as_optional` — the only optionality adjustment the surfaces need.
- :func:`request_field_definition` — rebuild a ``(annotation, FieldInfo)`` pair
  for a derived request model, carrying over metadata and constraints.

Typing note: a Python type annotation is not expressible as one static type — it
may be a class, a union, ``Annotated[...]``, ``Literal[...]`` or a parametrized
generic alias. ``Annotation`` is an ``Any`` alias that documents "this value is
a type annotation" at every boundary that traffics in them.

Consumed by ``param_policy.derive`` only.
"""

from __future__ import annotations

from functools import reduce
from operator import or_
from typing import Annotated, Any, Literal, TypeAlias, get_args, get_origin

from pydantic import Field
from pydantic.fields import FieldInfo

from unique_search_proxy_core.param_policy.exposable_param import (
    exposable_param_inner_type,
    flatten_union_args,
    is_exposable_param_type,
)

#: A Python type annotation object (see module docstring).
Annotation: TypeAlias = Any

#: A ``create_model`` field spec: ``(annotation, FieldInfo)``.
FieldDefinition: TypeAlias = tuple[Annotation, Any]

_COLLECTION_ORIGINS: tuple[type, ...] = (dict, list, tuple, set, frozenset)


def _union_of(members: list[Annotation]) -> Annotation:
    """Combine annotations with ``|`` (``[int, str]`` -> ``int | str``)."""
    return reduce(or_, members)


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
    if is_exposable_param_type(annotation):
        annotation = exposable_param_inner_type(annotation)
    return _normalize(annotation)


def as_optional(annotation: Annotation) -> Annotation:
    """Ensure the annotation admits ``None`` (idempotent when already optional)."""
    if type(None) in flatten_union_args(annotation):
        return annotation
    return annotation | None


def request_field_definition(
    field_info: FieldInfo,
    *,
    annotation: Annotation,
    default_none: bool = False,
) -> FieldDefinition:
    """Rebuild a ``(annotation, FieldInfo)`` pair for a derived request model.

    Carries over the config field's metadata (title, description, aliases,
    ``json_schema_extra``) and constraints (``ge``/``le``/``min_length``/…,
    stored by Pydantic as annotated-types objects in ``FieldInfo.metadata`` and
    re-attached here via ``Annotated``). ``default_none=True`` forces an
    optional ``None`` default (used when an ``ExposableParam`` knob is
    unwrapped: the admin default is merged at search time, never baked into the
    request schema).
    """
    if field_info.metadata:
        annotation = Annotated[annotation, *field_info.metadata]

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

    if default_none:
        return (annotation, Field(default=None, **field_kwargs))
    if field_info.is_required():
        return (annotation, Field(..., **field_kwargs))
    default = field_info.get_default(call_default_factory=True)
    return (annotation, Field(default=default, **field_kwargs))
