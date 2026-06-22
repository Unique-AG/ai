from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, cast, get_args, get_origin

from pydantic import SecretStr
from pydantic.fields import FieldInfo

from unique_search_proxy_client.web.settings.secret_str import (
    NOT_PROVIDED,
    LogSecretStr,
    field_has_not_provided_default,
)

_URI_DEFAULT_RE = re.compile(r"^https?://", re.IGNORECASE)

DEFAULT_HELM_SECTION = "connection"


def snake_to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


def env_var_name(field_name: str, env_prefix: str) -> str:
    return f"{env_prefix}{field_name.upper()}"


def _helm_extra(field_info: FieldInfo) -> dict[str, Any]:
    extra = field_info.json_schema_extra
    if isinstance(extra, dict):
        helm = extra.get("helm")
        if isinstance(helm, dict):
            return helm
    return {}


def _unwrap_annotation(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is None:
        return annotation
    args = get_args(annotation)
    non_none = [arg for arg in args if arg is not type(None)]
    if len(non_none) == 1:
        return non_none[0]
    return annotation


def _is_secret_type(annotation: Any) -> bool:
    inner = _unwrap_annotation(annotation)
    return inner in {SecretStr, LogSecretStr}


def _is_scalar_type(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin is Literal:
        return True
    inner = _unwrap_annotation(annotation)
    if inner in {str, int, float, bool}:
        return True
    if isinstance(inner, type) and issubclass(inner, str):
        return True
    return False


def _is_list_str_type(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin is not list:
        return False
    args = get_args(annotation)
    if not args:
        return False
    inner = args[0]
    return inner is str or (isinstance(inner, type) and issubclass(inner, str))


def _factory_takes_validated_data(factory: Callable[..., Any]) -> bool:
    try:
        params = inspect.signature(factory).parameters
    except (TypeError, ValueError):
        return False
    return any(
        p.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
        )
        for p in params.values()
    )


def _default_value(field_info: FieldInfo) -> Any:
    factory = field_info.default_factory
    if factory is not None:
        factory = cast(Callable[..., Any], factory)
        try:
            if _factory_takes_validated_data(factory):
                return factory({})
            return factory()
        except TypeError:
            return None
    return field_info.default


def _default_is_uri(default: Any) -> bool:
    return isinstance(default, str) and bool(_URI_DEFAULT_RE.match(default))


@dataclass(frozen=True)
class HelmFieldSpec:
    """One Helm-mapped field derived from a Pydantic model field."""

    python_name: str
    helm_name: str
    env_var: str
    sensitive: bool
    required_when_enabled: bool
    schema_ref: str | None
    plain_type: str | None
    format_uri: bool
    default: Any
    section: str
    block_level: bool
    container: bool
    emit_in_template: bool
    emit_in_values: bool


def _schema_ref_for_field(
    *,
    field_info: FieldInfo,
    sensitive: bool,
    default: Any,
    helm_extra: dict[str, Any],
) -> tuple[str | None, str | None]:
    override = helm_extra.get("value_source")
    if isinstance(override, str):
        return f"#/$defs/valueSource{override}", None

    if sensitive:
        return "#/$defs/valueSourceSensitive", None

    inner = _unwrap_annotation(field_info.annotation)
    if inner is bool:
        return "#/$defs/valueSourceBoolean", None
    if inner is int:
        return "#/$defs/valueSourceInteger", None
    if inner is float:
        return None, "number"
    if _default_is_uri(default):
        return None, "string"
    if inner is str or (isinstance(inner, type) and issubclass(inner, str)):
        return "#/$defs/valueSourceString", None
    return "#/$defs/valueSourceString", None


def iter_helm_fields(
    model: type[Any],
    *,
    env_prefix: str,
) -> tuple[HelmFieldSpec, ...]:
    specs: list[HelmFieldSpec] = []
    for field_name, field_info in model.model_fields.items():
        helm_extra = _helm_extra(field_info)
        if helm_extra.get("skip"):
            continue

        annotation = field_info.annotation
        origin = get_origin(annotation)
        container = False
        if origin is dict:
            continue
        if origin is list:
            if not _is_list_str_type(annotation):
                continue
            container = True
        elif not _is_scalar_type(annotation) and not _is_secret_type(annotation):
            continue

        default = _default_value(field_info)
        sensitive = bool(helm_extra.get("sensitive")) or _is_secret_type(annotation)
        required_when_enabled = bool(
            helm_extra.get("required_when_enabled")
        ) or field_has_not_provided_default(field_info)
        schema_ref, plain_type = _connection_property_types(
            field_info=field_info,
            sensitive=sensitive,
            default=default,
            helm_extra=helm_extra,
            container=container,
        )
        helm_name = str(helm_extra.get("helm_name", snake_to_camel(field_name)))
        section = str(helm_extra.get("section", DEFAULT_HELM_SECTION))
        block_level = bool(helm_extra.get("block_level"))
        spec = HelmFieldSpec(
            python_name=field_name,
            helm_name=helm_name,
            env_var=env_var_name(field_name, env_prefix),
            sensitive=sensitive,
            required_when_enabled=required_when_enabled,
            schema_ref=schema_ref,
            plain_type=plain_type,
            format_uri=_default_is_uri(default),
            default=default,
            section=section,
            block_level=block_level,
            container=container,
            emit_in_template=False,
            emit_in_values=True,
        )
        specs.append(
            HelmFieldSpec(
                python_name=spec.python_name,
                helm_name=spec.helm_name,
                env_var=spec.env_var,
                sensitive=spec.sensitive,
                required_when_enabled=spec.required_when_enabled,
                schema_ref=spec.schema_ref,
                plain_type=spec.plain_type,
                format_uri=spec.format_uri,
                default=spec.default,
                section=spec.section,
                block_level=spec.block_level,
                container=spec.container,
                emit_in_template=_should_emit_in_template(spec),
                emit_in_values=spec.emit_in_values,
            )
        )
    return tuple(specs)


def _connection_property_types(
    *,
    field_info: FieldInfo,
    sensitive: bool,
    default: Any,
    helm_extra: dict[str, Any],
    container: bool,
) -> tuple[str | None, str | None]:
    if container:
        return None, None
    return _schema_ref_for_field(
        field_info=field_info,
        sensitive=sensitive,
        default=default,
        helm_extra=helm_extra,
    )


def _should_emit_in_template(field: HelmFieldSpec) -> bool:
    if field.container:
        return False
    if field.required_when_enabled or field.sensitive:
        return True
    # Optional fields default to ``None`` (no literal in values.yaml) but are
    # still settable via overlays, so they must be emitted — guarded so the env
    # var only renders when the overlay actually provides a value.
    return field.default is not NOT_PROVIDED


def literal_default_for_values(field: HelmFieldSpec) -> str | int | float | bool | None:
    if field.container:
        return None
    if field.sensitive or field.required_when_enabled:
        return None
    default = field.default
    if isinstance(default, SecretStr):
        default = default.get_secret_value()
    if default is NOT_PROVIDED:
        return None
    if default is None:
        return None
    if isinstance(default, (str, int, float, bool)):
        return default
    return str(default)


def container_default_items(field: HelmFieldSpec) -> tuple[str, ...] | None:
    if not field.container:
        return None
    default = field.default
    if not isinstance(default, list):
        return None
    return tuple(str(item) for item in default)


def group_fields_by_section(
    fields: tuple[HelmFieldSpec, ...],
) -> tuple[tuple[str, tuple[HelmFieldSpec, ...]], ...]:
    """Group fields by section; ``connection`` first, then declaration order."""
    by_section: dict[str, list[HelmFieldSpec]] = {}
    section_order: list[str] = []
    for field in fields:
        if field.block_level:
            continue
        if field.section not in by_section:
            by_section[field.section] = []
            section_order.append(field.section)
        by_section[field.section].append(field)

    ordered_names: list[str] = []
    if DEFAULT_HELM_SECTION in by_section:
        ordered_names.append(DEFAULT_HELM_SECTION)
    for name in section_order:
        if name != DEFAULT_HELM_SECTION:
            ordered_names.append(name)

    return tuple((name, tuple(by_section[name])) for name in ordered_names)


def block_level_fields(
    fields: tuple[HelmFieldSpec, ...],
) -> tuple[HelmFieldSpec, ...]:
    return tuple(field for field in fields if field.block_level)
