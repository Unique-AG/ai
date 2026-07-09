"""Tool JSON Schema fields for LLM-exposed engine parameters (no HTTP)."""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, Field, create_model

from unique_search_proxy_core.param_policy.annotations import Annotation, as_optional
from unique_search_proxy_core.param_policy.field_plan import field_plan
from unique_search_proxy_core.param_policy.resolver import ConfigRequestResolver


def exposed_field_names(config: BaseModel) -> list[str]:
    """Python field names exposed to LLM callers (``query`` excluded)."""
    return ConfigRequestResolver.exposed_field_names(config, with_query=False)


# JSON-schema key an exposed field stamps on its own node so the finalize pass
# can locate and clean it — including copies nested under ``$defs`` — without
# threading field-name lists through every call site. Removed before output.
_EXPOSED_FIELD_MARKER = "x-unique-exposed-tool-field"

#: Class attribute stamped on dynamically built tool-parameter models.
EXPOSED_FIELD_NAMES_ATTR = "__exposed_field_names__"


def _stamp_exposed_field_names(
    model: type[BaseModel],
    exposed_field_defs: dict[str, tuple[Annotation, Any]] | None,
) -> type[BaseModel]:
    names: tuple[str, ...] = (
        tuple(exposed_field_defs.keys()) if exposed_field_defs else ()
    )
    setattr(model, EXPOSED_FIELD_NAMES_ATTR, names)
    return model


def _mark_exposed_tool_field(field_schema: dict[str, Any]) -> None:
    """``json_schema_extra`` hook: strip the default and flag the node for cleanup.

    ``default`` can be dropped here, but Pydantic re-adds a ``title`` from the
    field name *after* this hook runs, so title removal is deferred to
    :func:`finalize_exposed_tool_schema` via the marker stamped here.
    """
    field_schema.pop("default", None)
    field_schema[_EXPOSED_FIELD_MARKER] = True


def finalize_exposed_tool_schema(node: Any) -> None:
    """Strip ``title``/``default`` (and the marker) from exposed field nodes in-place.

    Walks the fully rendered schema so marked nodes are cleaned wherever they
    appear, including nested definitions under ``$defs``.
    """
    if isinstance(node, dict):
        if node.pop(_EXPOSED_FIELD_MARKER, None):
            node.pop("title", None)
            node.pop("default", None)
        for value in node.values():
            finalize_exposed_tool_schema(value)
    elif isinstance(node, list):
        for item in node:
            finalize_exposed_tool_schema(item)


class ExposedToolParameterModel(BaseModel):
    """Base for tool-parameter models that carry engine-exposed fields.

    Overrides ``model_json_schema`` once (inherited by every dynamically built
    tool-parameter model) to finalize exposed fields — dropping the Pydantic
    ``title``/``default`` noise that must not leak into the LLM tool manifest.
    """

    @classmethod
    def exposed_field_names_for_model(cls) -> tuple[str, ...]:
        """Snake_case Python names exposed on this tool-parameter model."""
        return getattr(cls, EXPOSED_FIELD_NAMES_ATTR, ())

    @classmethod
    def with_exposed_fields(
        cls,
        exposed_field_defs: dict[str, tuple[Annotation, Any]] | None,
        *,
        extra_field_defs: dict[str, tuple[Annotation, Any]] | None = None,
    ) -> type[ExposedToolParameterModel]:
        """Build a subclass with optional engine knobs plus any fixed fields."""
        if exposed_field_defs is None and not extra_field_defs:
            return cls
        field_defs: dict[str, tuple[Any, Any]] = dict(extra_field_defs or {})
        if exposed_field_defs:
            field_defs.update(exposed_field_defs)
        if not field_defs:
            return cls
        model = create_model(
            cls.__name__,
            __base__=cls,
            **cast(Any, field_defs),
        )
        return cast(
            type[ExposedToolParameterModel],
            _stamp_exposed_field_names(model, exposed_field_defs),
        )

    @classmethod
    def model_json_schema(cls, *args: Any, **kwargs: Any) -> dict[str, Any]:
        schema = super().model_json_schema(*args, **kwargs)
        finalize_exposed_tool_schema(schema)
        return schema


def build_exposed_tool_field_defs(
    config: BaseModel,
) -> dict[str, tuple[Annotation, Any]] | None:
    """Flat ``create_model`` field defs for tool schemas (description-only, optional).

    A thin adapter over the exposed subset of :func:`field_plan`: each exposed
    knob becomes an optional field keyed by its Python name, exposed to callers
    under its camelCase alias. Admin defaults are not embedded in the tool schema
    (they are merged at search time); each field marks its own schema node so
    :class:`ExposedToolParameterModel` can strip the ``title``/``default`` noise.
    """
    exposed = set(exposed_field_names(config))
    if not exposed:
        return None
    return {
        plan.name: (
            as_optional(plan.inner_type),
            Field(
                default=None,
                description=plan.description,
                alias=plan.alias,
                json_schema_extra=_mark_exposed_tool_field,
            ),
        )
        for plan in field_plan(type(config))
        if plan.name in exposed
    }


__all__ = [
    "ExposedToolParameterModel",
    "build_exposed_tool_field_defs",
    "exposed_field_names",
]
