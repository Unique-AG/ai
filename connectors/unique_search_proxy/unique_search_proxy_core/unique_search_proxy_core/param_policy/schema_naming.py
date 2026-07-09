"""Readable OpenAPI ``$defs`` names for parametrized ``ExposableParam`` generics.

Pydantic names a parametrized generic (and derives its JSON Schema ``$defs`` key
and generated-SDK file name) from the full ``Annotated[..., FieldInfo(...)]`` repr
of the type argument, which is unreadable. These helpers derive a short label
(e.g. ``ExposableStr``) from the inner type so the config schema exposed to the
admin RJSF UI and the generated SDK stay clean. This is purely cosmetic and kept
separate from the expose/value domain of :class:`ExposableParam`.
"""

from __future__ import annotations

import types
from typing import Any, Literal, Union, cast, get_args, get_origin

from pydantic_core import CoreSchema


def _strip_annotated(annotation: Any) -> Any:
    from typing import Annotated

    if get_origin(annotation) is Annotated:
        args = get_args(annotation)
        if args:
            return _strip_annotated(args[0])
    return annotation


def _pascal(text: str) -> str:
    parts = [segment for segment in text.replace("-", "_").split("_") if segment]
    if not parts:
        return "".join(ch for ch in text if ch.isalnum()).capitalize() or "Value"
    return "".join(segment[:1].upper() + segment[1:] for segment in parts)


def _type_label(annotation: Any) -> str:
    annotation = _strip_annotated(annotation)
    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        non_none = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(non_none) == 1:
            return _type_label(non_none[0])
        return "Or".join(_type_label(arg) for arg in non_none) or "Value"
    if origin is Literal:
        return "".join(_pascal(str(value)) for value in get_args(annotation)) or "Value"
    if isinstance(annotation, type):
        return _pascal(annotation.__name__)
    return "Value"


def exposable_schema_name(params: tuple[type[Any], ...]) -> str:
    """Clean parametrized-generic name, e.g. ``ExposableStr`` (drives ``$defs`` title)."""
    return "Exposable" + "".join(_type_label(param) for param in params)


def clean_generic_ref(cls: type[Any], schema: CoreSchema) -> CoreSchema:
    """Rewrite a parametrized generic's core ``ref`` so its ``$defs`` key is readable.

    ``model_parametrized_name`` only cleans the schema ``title``; the ``$defs`` key
    (and generated SDK file name) come from the core-schema ``ref``. Rewrite the
    ``ref`` to the clean parametrized name so definition key and title match.
    """
    metadata = getattr(cls, "__pydantic_generic_metadata__", None)
    if isinstance(metadata, dict) and metadata.get("args") and schema.get("ref"):
        clean_ref = f"{cls.__module__}.{cls.__name__}:{id(cls)}"
        return cast(CoreSchema, {**schema, "ref": clean_ref})
    return schema


__all__ = ["clean_generic_ref", "exposable_schema_name"]
