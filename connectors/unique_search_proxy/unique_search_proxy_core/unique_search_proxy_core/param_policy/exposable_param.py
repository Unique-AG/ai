"""Optional provider knobs: admin default (``value``) and LLM visibility (``expose``)."""

from __future__ import annotations

import types
from typing import (
    Annotated,
    Any,
    Generic,
    Literal,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

from pydantic import BaseModel, Field, GetCoreSchemaHandler, model_validator
from pydantic.fields import FieldInfo
from pydantic_core import CoreSchema

from unique_search_proxy_core.schema import camelized_model_config

T = TypeVar("T")


def _exposable_type_label(annotation: Any) -> str:
    """Build a short, stable PascalCase label for an ``ExposableParam`` type arg.

    Used to give parametrized generics a clean OpenAPI schema name (and therefore
    a clean generated SDK model file name) instead of Pydantic's default, which
    embeds the full ``Annotated[..., FieldInfo(...)]`` repr.
    """
    annotation = _strip_annotated(annotation)
    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        non_none = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(non_none) == 1:
            return _exposable_type_label(non_none[0])
        return "Or".join(_exposable_type_label(arg) for arg in non_none) or "Value"
    if origin is Literal:
        return "".join(_pascal(str(value)) for value in get_args(annotation)) or "Value"
    if isinstance(annotation, type):
        return _pascal(annotation.__name__)
    return "Value"


def _pascal(text: str) -> str:
    parts = [segment for segment in text.replace("-", "_").split("_") if segment]
    if not parts:
        return "".join(ch for ch in text if ch.isalnum()).capitalize() or "Value"
    return "".join(segment[:1].upper() + segment[1:] for segment in parts)


class ExposableParam(BaseModel, Generic[T]):
    """Deployment setting for an optional provider parameter.

    Parent config fields use ``ExposableParam[Annotated[T | None, DeactivatedNone]]`` with
    ``Field(default_factory=lambda: ExposableParam(expose=False, value=None))``.

    - ``value is None``: deactivated (no merge, not on LLM schema unless ``expose`` alone matters).
    - ``expose=False`` and ``value`` set: merge default; omit from LLM schema.
    - ``expose=True``: include on LLM call schema; merge ``value`` when not ``None``.
    - ``value`` omitted in JSON: parent config merges from field ``default_factory`` before validation.
    - ``value: null`` in JSON: explicit deactivation (merge skipped; does not inherit factory).
    """

    model_config = camelized_model_config
    expose: bool = Field(
        description="When true, this parameter is included on the LLM call JSON Schema.",
    )
    value: T = Field(
        description="Admin default merged into each search when not ``None``.",
    )

    def merged_value(self) -> T:
        return self.value

    def llm_exposed(self) -> bool:
        return self.expose

    def is_active(self) -> bool:
        """True when a non-null admin default should be merged."""
        return self.value is not None

    @classmethod
    def model_parametrized_name(cls, params: tuple[type[Any], ...]) -> str:
        """Clean schema name for parametrized generics (drives OpenAPI ``$defs`` keys).

        Without this, Pydantic names ``ExposableParam[Annotated[str | None, ...]]``
        after the full annotation repr, producing unreadable OpenAPI component names
        and generated SDK file names. We derive a short label from the inner type, e.g.
        ``ExposableStr`` or ``ExposableEI``.
        """
        return "Exposable" + "".join(_exposable_type_label(param) for param in params)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source: type[Any],
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Give parametrized generics a clean core ``ref`` so OpenAPI ``$defs`` keys are readable.

        Pydantic derives the JSON Schema ``$defs`` key (and generated SDK file name)
        from the core schema ``ref``, which for a parametrized generic embeds the full
        ``Annotated[..., FieldInfo(...)]`` repr of the type argument. ``model_parametrized_name``
        only cleans the schema ``title``, not the ``ref``. Here we rewrite the ``ref`` to the
        clean parametrized name (e.g. ``ExposableStr``/``ExposableEI``) so the definition key
        matches the title.
        """
        schema = handler(source)
        metadata = getattr(cls, "__pydantic_generic_metadata__", None)
        if isinstance(metadata, dict) and metadata.get("args") and schema.get("ref"):
            clean_ref = f"{cls.__module__}.{cls.__name__}:{id(cls)}"
            return cast(CoreSchema, {**schema, "ref": clean_ref})
        return schema

    @model_validator(mode="before")
    @classmethod
    def _coerce_input(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"expose": False, "value": data}
        if isinstance(data, dict) and "expose" not in data and "value" not in data:
            return data
        return data


def _exposable_field_keys(field_name: str, field_info: FieldInfo) -> list[str]:
    keys = [field_name]
    if field_info.alias is not None:
        keys.insert(0, field_info.alias)
    if (
        field_info.serialization_alias is not None
        and field_info.serialization_alias not in keys
    ):
        keys.append(field_info.serialization_alias)
    return keys


def merge_exposable_params_with_factory_defaults(
    model_cls: type[BaseModel],
    data: Any,
) -> Any:
    """Merge partial exposable JSON with each field's ``default_factory`` (like ``search_engine_id``)."""
    if not isinstance(data, dict):
        return data
    out = dict(data)
    for field_name, field_info in model_cls.model_fields.items():
        if not is_exposable_param_field(field_info):
            continue
        payload_key: str | None = None
        payload: Any = None
        for key in _exposable_field_keys(field_name, field_info):
            if key in out:
                payload_key = key
                payload = out[key]
                break
        if payload_key is None or not isinstance(payload, dict):
            continue
        if "value" in payload:
            continue
        factory_default = field_info.get_default(call_default_factory=True)
        if not isinstance(factory_default, ExposableParam):
            continue
        out[payload_key] = {
            **factory_default.model_dump(mode="python"),
            **payload,
        }
    return out


def _pydantic_parametrized_args(annotation: Any) -> tuple[Any, ...]:
    meta = getattr(annotation, "__pydantic_generic_metadata__", None)
    if not isinstance(meta, dict):
        return ()
    args = meta.get("args")
    if not args:
        return ()
    return tuple(args)


def _strip_annotated(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is Annotated:
        args = get_args(annotation)
        if args:
            return _strip_annotated(args[0])
    return annotation


def is_exposable_param_type(annotation: Any) -> bool:
    if _pydantic_parametrized_args(annotation):
        return True
    origin = get_origin(annotation)
    if origin is not None:
        if origin is ExposableParam:
            return True
        args = get_args(annotation)
        return any(is_exposable_param_type(arg) for arg in args)
    return isinstance(annotation, type) and issubclass(annotation, ExposableParam)


def is_exposable_param_field(field_info: FieldInfo) -> bool:
    return is_exposable_param_type(field_info.annotation)


def flatten_union_args(annotation: Any) -> tuple[Any, ...]:
    annotation = _strip_annotated(annotation)
    origin = get_origin(annotation)
    if origin is None:
        return (annotation,)
    args = get_args(annotation)
    if not args:
        return (annotation,)
    return args


def exposable_param_inner_type(annotation: Any) -> Any:
    """Plain inner ``T`` for derived request / LLM models (strips ``ExposableParam`` and ``Annotated``)."""
    pydantic_args = _pydantic_parametrized_args(annotation)
    if pydantic_args:
        return _strip_annotated(pydantic_args[0])

    origin = get_origin(annotation)
    if origin is not None:
        args = get_args(annotation)
        if origin is ExposableParam and args:
            return _strip_annotated(args[0])
        inner_parts: list[Any] = []
        for arg in args:
            if arg is type(None):
                inner_parts.append(type(None))
                continue
            if is_exposable_param_type(arg):
                inner_parts.append(exposable_param_inner_type(arg))
            else:
                inner_parts.append(_strip_annotated(arg))
        if not inner_parts:
            return str
        if len(inner_parts) == 1:
            return inner_parts[0]
        return Union[tuple(inner_parts)]  # type: ignore[return-value]
    if annotation is ExposableParam:
        return str
    return _strip_annotated(annotation)


def unwrap_exposable_param_value(value: Any) -> Any:
    if isinstance(value, ExposableParam):
        return value.merged_value()
    return value
