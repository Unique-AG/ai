from __future__ import annotations

from unique_search_proxy_client.web.helm.generator.introspect import (
    iter_helm_fields,
    literal_default_for_values,
)
from unique_search_proxy_client.web.helm.registry import HelmSettingsGroup

_VALUES_BEGIN = "# @helm-gen:begin providers"
_VALUES_END = "# @helm-gen:end providers"


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


def _render_provider_block(group: HelmSettingsGroup) -> list[str]:
    assert group.helm_key is not None
    lines = [f"{group.helm_key}:", "  enabled: false"]
    fields = iter_helm_fields(group.model, env_prefix=group.env_prefix)
    literal_lines: list[str] = []
    comment_lines: list[str] = []
    for field in fields:
        default = literal_default_for_values(field)
        if default is not None:
            literal_lines.append(f"    {field.helm_name}: {_yaml_scalar(default)}")
        elif field.required_when_enabled or field.sensitive:
            label = field.helm_name
            if field.sensitive:
                comment_lines.append(f"  # {label}: <fromSecret or fromSecretProvider>")
            else:
                comment_lines.append(
                    f"  # {label}: <set in cluster overlay when enabled>"
                )
    lines.extend(comment_lines)
    lines.append("  connection:")
    if literal_lines:
        lines.extend(literal_lines)
    else:
        lines.append("    {}")
    return lines


def render_provider_values_section(groups: tuple[HelmSettingsGroup, ...]) -> str:
    lines = [_VALUES_BEGIN]
    for index, group in enumerate(groups):
        if index > 0:
            lines.append("")
        lines.extend(_render_provider_block(group))
    lines.append("")
    lines.append("# urlSafety: omitted in v1 (lists use code defaults)")
    lines.append(_VALUES_END)
    return "\n".join(lines) + "\n"


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
