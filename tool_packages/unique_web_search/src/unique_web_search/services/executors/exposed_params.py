"""Helpers for injecting engine-exposed parameters into tool schemas."""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel
from unique_search_proxy_core.search_engines.call_schema import (
    strip_exposed_tool_schema_noise,
)

__all__ = [
    "attach_exposed_schema_cleanup",
    "collect_flat_exposed_params",
    "strip_tool_schema_noise",
]


def collect_flat_exposed_params(
    source: BaseModel,
    field_names: list[str],
) -> dict[str, Any]:
    """Collect non-null exposed engine params from flat tool fields."""
    return {
        name: value
        for name in field_names
        if (value := getattr(source, name, None)) is not None
    }


def strip_tool_schema_noise(
    schema: dict[str, Any],
    *,
    field_names: list[str],
) -> dict[str, Any]:
    """Remove ``title`` and ``default`` from exposed property nodes."""
    return strip_exposed_tool_schema_noise(schema, field_names=field_names)


def attach_exposed_schema_cleanup(
    model: type[BaseModel],
    exposed_field_names: list[str],
) -> type[BaseModel]:
    """Strip provider noise from JSON schema for dynamically injected exposed fields."""
    if not exposed_field_names:
        return model

    @classmethod
    def model_json_schema(
        cls,
        by_alias: bool = True,
        ref_template: str = "#/$defs/{model}",
        mode: str = "validation",
    ) -> dict[str, Any]:
        schema = BaseModel.model_json_schema.__func__(  # type: ignore[attr-defined]
            cls,
            by_alias=by_alias,
            ref_template=ref_template,
            mode=mode,
        )
        return strip_exposed_tool_schema_noise(
            schema,
            field_names=exposed_field_names,
        )

    model.model_json_schema = model_json_schema  # type: ignore[method-assign]
    return model


def create_model_with_exposed_fields(
    name: str,
    base: type[BaseModel],
    field_defs: dict[str, tuple[Any, Any]],
    exposed_field_names: list[str],
) -> type[BaseModel]:
    """Create a dynamic tool model and attach exposed-field JSON schema cleanup."""
    from pydantic import create_model

    model = create_model(
        name,
        __base__=base,
        **cast(Any, field_defs),
    )
    return attach_exposed_schema_cleanup(model, exposed_field_names)
