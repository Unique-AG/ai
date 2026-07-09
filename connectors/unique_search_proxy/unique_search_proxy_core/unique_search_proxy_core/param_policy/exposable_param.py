"""Optional provider knobs: admin default (``value``) and LLM visibility (``expose``)."""

from __future__ import annotations

from typing import (
    Annotated,
    Any,
    Generic,
    Literal,
    TypeVar,
    get_args,
    get_origin,
)

from pydantic import BaseModel, Field, GetCoreSchemaHandler
from pydantic.fields import FieldInfo
from pydantic_core import CoreSchema

from unique_search_proxy_core.param_policy.schema_naming import (
    clean_generic_ref,
    exposable_schema_name,
)
from unique_search_proxy_core.schema import camelized_model_config

T = TypeVar("T")


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

    def is_active(self) -> bool:
        """True when a non-null admin default should be merged."""
        return self.value is not None

    @classmethod
    def model_parametrized_name(cls, params: tuple[type[Any], ...]) -> str:
        return exposable_schema_name(params)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source: type[Any],
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        return clean_generic_ref(cls, handler(source))


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


def pydantic_parametrized_args(annotation: Any) -> tuple[Any, ...]:
    """Type args of a parametrized Pydantic generic (``ExposableParam[T]`` -> ``(T,)``)."""
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
    if pydantic_parametrized_args(annotation):
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
    if origin is Literal:
        return (annotation,)
    args = get_args(annotation)
    if not args:
        return (annotation,)
    return args
