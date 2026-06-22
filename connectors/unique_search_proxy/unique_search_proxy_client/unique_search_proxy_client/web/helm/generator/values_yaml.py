from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files

from jinja2 import Environment, StrictUndefined, Template

from unique_search_proxy_client.web.helm.generator.introspect import (
    block_level_fields,
    container_default_items,
    group_fields_by_section,
    iter_helm_fields,
    literal_default_for_values,
)
from unique_search_proxy_client.web.helm.registry import HelmSettingsGroup

_VALUES_BEGIN = "# @helm-gen:begin providers"
_VALUES_END = "# @helm-gen:end providers"

_TEMPLATE_PACKAGE = "unique_search_proxy_client.web.helm.generator"
_TEMPLATE_NAME = "provider_values_yaml.j2"

_SENSITIVE_PLACEHOLDER = "<fromSecret or fromSecretProvider>"
_REQUIRED_PLACEHOLDER = "<set in cluster overlay when enabled>"
_CONTAINER_NOTE = "code default, not env-overridable"


def _yaml_scalar(value: str | int | float | bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if value == "":
        return '""'
    if any(ch in value for ch in ":{}[]&*#?|>-!%@`"):
        return json_quote(value)
    return value


def json_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


@dataclass(frozen=True)
class _ValueRow:
    """One values.yaml line or commented placeholder under a section."""

    helm_name: str
    literal: str | None = None
    placeholder: str | None = None
    container_items: tuple[str, ...] | None = None


@dataclass(frozen=True)
class _SectionBlock:
    name: str
    rows: tuple[_ValueRow, ...]

    @property
    def has_values(self) -> bool:
        """True when at least one row renders an actual YAML key.

        Sections whose rows are all commented placeholders (sensitive or
        container fields) would otherwise serialise to ``null`` and fail
        schema validation, so the template emits ``{}`` for them.
        """
        return any(row.literal is not None for row in self.rows)


@dataclass(frozen=True)
class _ProviderBlock:
    helm_key: str
    kind: str
    enabled_literal: str | None
    sections: tuple[_SectionBlock, ...]


@lru_cache(maxsize=1)
def _template() -> Template:
    text = (
        files(_TEMPLATE_PACKAGE)
        .joinpath("templates", _TEMPLATE_NAME)
        .read_text(encoding="utf-8")
    )
    env = Environment(
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=False,
        undefined=StrictUndefined,
    )
    return env.from_string(text)


def _rows_for_fields(fields: tuple) -> tuple[_ValueRow, ...]:
    literal_rows: list[_ValueRow] = []
    comment_rows: list[_ValueRow] = []
    for field in fields:
        container_items = container_default_items(field)
        if container_items is not None:
            comment_rows.append(
                _ValueRow(field.helm_name, container_items=container_items)
            )
            continue
        default = literal_default_for_values(field)
        if default is not None:
            literal_rows.append(
                _ValueRow(field.helm_name, literal=_yaml_scalar(default))
            )
        elif field.required_when_enabled or field.sensitive:
            placeholder = (
                _SENSITIVE_PLACEHOLDER if field.sensitive else _REQUIRED_PLACEHOLDER
            )
            comment_rows.append(_ValueRow(field.helm_name, placeholder=placeholder))
    return tuple(literal_rows + comment_rows)


def _provider_block(group: HelmSettingsGroup) -> _ProviderBlock:
    fields = iter_helm_fields(group.model, env_prefix=group.env_prefix)
    if group.kind == "urlSafety":
        enabled_literal = None
        for block_field in block_level_fields(fields):
            default = literal_default_for_values(block_field)
            if default is not None:
                enabled_literal = _yaml_scalar(default)
        sections = tuple(
            _SectionBlock(name, _rows_for_fields(section_fields))
            for name, section_fields in group_fields_by_section(fields)
        )
        return _ProviderBlock(
            helm_key=group.helm_key or "",
            kind=group.kind,
            enabled_literal=enabled_literal,
            sections=sections,
        )

    sections = tuple(
        _SectionBlock(name, _rows_for_fields(section_fields))
        for name, section_fields in group_fields_by_section(fields)
    )
    return _ProviderBlock(
        helm_key=group.helm_key or "",
        kind=group.kind,
        enabled_literal=None,
        sections=sections,
    )


def render_provider_values_section(groups: tuple[HelmSettingsGroup, ...]) -> str:
    blocks = []
    for group in groups:
        assert group.helm_key is not None
        blocks.append(_provider_block(group))
    return _template().render(
        begin_marker=_VALUES_BEGIN,
        end_marker=_VALUES_END,
        groups=blocks,
        container_note=_CONTAINER_NOTE,
    )


def patch_values_yaml(
    values_text: str,
    groups: tuple[HelmSettingsGroup, ...],
) -> str:
    begin_index = values_text.find(_VALUES_BEGIN)
    end_index = values_text.find(_VALUES_END)
    if begin_index == -1 or end_index == -1 or end_index < begin_index:
        raise ValueError(
            f"values.yaml must contain {_VALUES_BEGIN} and {_VALUES_END} markers"
        )

    end_index += len(_VALUES_END)
    generated = render_provider_values_section(groups).rstrip("\n")
    prefix = values_text[:begin_index].rstrip("\n")
    suffix = values_text[end_index:].lstrip("\n")
    if suffix:
        return f"{prefix}\n\n{generated}\n\n{suffix}"
    return f"{prefix}\n\n{generated}\n"
