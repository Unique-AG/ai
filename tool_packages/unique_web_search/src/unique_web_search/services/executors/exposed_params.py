"""Runtime collection of engine-exposed parameters from validated tool calls."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

__all__ = ["collect_flat_exposed_params"]


def collect_flat_exposed_params(source: BaseModel) -> dict[str, Any]:
    """Collect non-null exposed engine params from flat tool fields.

    Field names are read from the parameter model class (stamped at schema-build
    time by :meth:`ExposedToolParameterModel.with_exposed_fields`).
    """
    field_names = type(source).exposed_field_names_for_model()
    return {
        name: value
        for name in field_names
        if (value := getattr(source, name, None)) is not None
    }
