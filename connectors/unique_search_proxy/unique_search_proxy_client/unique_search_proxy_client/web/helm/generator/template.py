from __future__ import annotations

from unique_search_proxy_client.web.helm.generator.introspect import (
    HelmFieldSpec,
    iter_helm_fields,
)
from unique_search_proxy_client.web.helm.metadata import (
    EgressDomainWildcard,
    EgressEndpointField,
)
from unique_search_proxy_client.web.helm.registry import HelmSettingsGroup

_GENERATED_HEADER = """{{/*
GENERATED — do not edit. Regenerate with:
  uv run python scripts/generate_helm_config.py

Generated Helm wiring for every @helm_settings group (search providers plus
internal config such as httpClient and urlSafety): env injection, Cilium egress
rules and secret-provider collection. Implemented as overrides of the shared base
library extension hooks (base.externalService.*.ext).
*/}}
"""


def _values_path(group: HelmSettingsGroup, field: HelmFieldSpec, *, hooks: bool) -> str:
    root = ".ctx.Values" if hooks else ".Values"
    if field.block_level:
        return f"{root}.{group.helm_key}.{field.helm_name}"
    return f"{root}.{group.helm_key}.{field.section}.{field.helm_name}"


def _fail_message(group: HelmSettingsGroup, field: HelmFieldSpec) -> str:
    if field.block_level:
        path = f"{group.helm_key}.{field.helm_name}"
    else:
        path = f"{group.helm_key}.{field.section}.{field.helm_name}"
    return (
        f"{path} is required when {group.helm_key}.enabled is true. "
        "Set it in your environment overlay."
    )


def _emit_env_field(
    group: HelmSettingsGroup,
    field: HelmFieldSpec,
    *,
    hooks: bool,
) -> list[str]:
    lines: list[str] = []
    connection_path = _values_path(group, field, hooks=hooks)

    if field.container:
        # Overridable list: JSON-encode so pydantic-settings parses it back into a
        # list[str] from the single env var. Always emitted; values.yaml carries
        # the code default and overlays replace the whole list.
        lines.append(
            f"- name: {field.env_var}\n"
            f"  value: {{{{ {connection_path} | toJson | quote }}}}"
        )
        return lines

    if field.sensitive:
        # Conditional wrappers use left-trim only ({{- ... }} / {{- end }}). A
        # right-trim ({{- ... -}}) on an empty/false block would also consume the
        # newline of the *following* always-emitted field, merging two env entries
        # onto one line and producing invalid YAML.
        if field.required_when_enabled:
            lines.append(f"{{{{- if not {connection_path} }}}}")
            lines.append(f'{{{{- fail "{_fail_message(group, field)}" }}}}')
            lines.append("{{- end }}")
        else:
            lines.append(f"{{{{- if {connection_path} }}}}")
        ctx = ".ctx" if hooks else "."
        lines.append(
            '{{ include "base.valueSource.env" (dict "name" '
            f'"{field.env_var}" "src" {connection_path} "ctx" {ctx}) '
            "}}"
        )
        if not field.required_when_enabled:
            lines.append("{{- end }}")
        return lines

    if field.required_when_enabled:
        lines.append(
            f"- name: {field.env_var}\n"
            f'  value: {{{{ required "{_fail_message(group, field)}" '
            f"{connection_path} | quote }}}}"
        )
    elif field.default is None:
        # Optional override with no literal default in values.yaml: only emit the
        # env var when the overlay sets it, so the service keeps its own default
        # instead of receiving an empty string. Left-trim only (see note above):
        # a right-trim here would swallow the next field's leading newline.
        lines.append(f"{{{{- if {connection_path} }}}}")
        lines.append(
            f"- name: {field.env_var}\n  value: {{{{ {connection_path} | quote }}}}"
        )
        lines.append("{{- end }}")
    else:
        lines.append(
            f"- name: {field.env_var}\n  value: {{{{ {connection_path} | quote }}}}"
        )
    return lines


def _emit_group_env_block(group: HelmSettingsGroup, *, hooks: bool) -> list[str]:
    field_lines: list[str] = []
    for field in iter_helm_fields(group.model, env_prefix=group.env_prefix):
        if not field.emit_in_template:
            continue
        field_lines.extend(_emit_env_field(group, field, hooks=hooks))

    # Only gated groups wrap their env injection in a synthetic ``enabled`` flag.
    # Non-gated groups (e.g. ``httpClient``, ``urlSafety``) are always-on; their
    # behaviour is driven by their own fields, so their env vars must always be
    # emitted. Gating them would silently drop config from overlays that set it
    # without the (chart-only) ``enabled: true``.
    if not group.gated:
        return field_lines

    # Left-trim only: a right-trim on the closing gate would consume the leading
    # newline of whatever follows (e.g. the always-on httpClient block), merging
    # the last gated env entry with the next one into invalid YAML.
    values_root = ".ctx.Values" if hooks else ".Values"
    return [
        f"{{{{- if and {values_root}.{group.helm_key} "
        f"{values_root}.{group.helm_key}.enabled }}}}",
        *field_lines,
        "{{- end }}",
    ]


def _find_helm_field(
    group: HelmSettingsGroup, python_name: str
) -> HelmFieldSpec | None:
    return next(
        (
            field
            for field in iter_helm_fields(group.model, env_prefix=group.env_prefix)
            if field.python_name == python_name
        ),
        None,
    )


def _emit_endpoint_field_egress(
    group: HelmSettingsGroup,
    egress: EgressEndpointField,
) -> list[str]:
    endpoint_field = _find_helm_field(group, egress.field_name)
    if endpoint_field is None:
        return []

    helm_endpoint = endpoint_field.helm_name
    fail_msg = _fail_message(group, endpoint_field)
    section = endpoint_field.section
    return [
        f"{{{{- if and .Values.{group.helm_key} .Values.{group.helm_key}.enabled -}}}}",
        f'{{{{- $endpoint := required "{fail_msg}" '
        f".Values.{group.helm_key}.{section}.{helm_endpoint} -}}}}",
        "{{- $parsed := urlParse $endpoint -}}",
        '{{- $hostParts := $parsed.host | splitList ":" -}}',
        "{{- $host := first $hostParts -}}",
        '{{- $port := "443" -}}',
        '{{- if eq $parsed.scheme "http" -}}{{- $port = "80" -}}{{- end -}}',
        "{{- if gt (len $hostParts) 1 -}}{{- $port = last $hostParts -}}{{- end -}}",
        "- toFQDNs:",
        "  - matchName: {{ $host | quote }}",
        "  toPorts:",
        "  - ports:",
        "    - port: {{ $port | quote }}",
        "      protocol: TCP",
        "{{- end -}}",
    ]


def _emit_domain_wildcard_egress(
    group: HelmSettingsGroup,
    egress: EgressDomainWildcard,
) -> list[str]:
    domain_field = _find_helm_field(group, egress.field_name)
    if domain_field is None:
        return []

    helm_domain = domain_field.helm_name
    fail_msg = _fail_message(group, domain_field)
    section = domain_field.section
    return [
        f"{{{{- if and .Values.{group.helm_key} .Values.{group.helm_key}.enabled -}}}}",
        f'{{{{- $domain := required "{fail_msg}" '
        f".Values.{group.helm_key}.{section}.{helm_domain} -}}}}",
        "- toFQDNs:",
        '  - matchPattern: {{ printf "*.%s" $domain | quote }}',
        "  toPorts:",
        "  - ports:",
        f'    - port: "{egress.port}"',
        "      protocol: TCP",
        "{{- end -}}",
    ]


def _emit_egress_block(group: HelmSettingsGroup) -> list[str]:
    egress = group.egress
    if isinstance(egress, EgressEndpointField):
        return _emit_endpoint_field_egress(group, egress)
    if isinstance(egress, EgressDomainWildcard):
        return _emit_domain_wildcard_egress(group, egress)
    return []


def _emit_has_rules_block(groups: tuple[HelmSettingsGroup, ...]) -> list[str]:
    checks = [
        f"(and .Values.{group.helm_key} .Values.{group.helm_key}.enabled)"
        for group in groups
        if group.egress is not None
    ]
    if not checks:
        return ["{{/* no auto egress rules */}}"]
    if len(checks) == 1:
        return [f"{{{{- if {checks[0]} -}}}}true{{{{- end -}}}}"]
    joined = " ".join(checks)
    return [f"{{{{- if or {joined} -}}}}true{{{{- end -}}}}"]


def _emit_secret_provider_block(groups: tuple[HelmSettingsGroup, ...]) -> list[str]:
    lines: list[str] = []
    for group in groups:
        sensitive_fields = [
            field
            for field in iter_helm_fields(group.model, env_prefix=group.env_prefix)
            if field.sensitive
        ]
        if not sensitive_fields:
            continue
        field_paths = [
            f".ctx.Values.{group.helm_key}.{field.section}.{field.helm_name}"
            if not field.block_level
            else f".ctx.Values.{group.helm_key}.{field.helm_name}"
            for field in sensitive_fields
        ]
        field_refs = " ".join(field_paths)
        include_line = (
            '{{ include "base.conn.secretProvider.fields" (dict "extByVault" .extByVault '
            f'"fields" (list {field_refs})) '
            "}}"
        )
        # Gated blocks collect secrets behind their synthetic ``enabled`` flag.
        # Non-gated blocks (e.g. ``httpClient``) have no such toggle, so collect
        # their secrets whenever at least one is configured — mirroring the
        # always-on env injection and avoiding a silently-dropped credential.
        if group.gated:
            guard = (
                f"and .ctx.Values.{group.helm_key} .ctx.Values.{group.helm_key}.enabled"
            )
        elif len(field_paths) == 1:
            guard = field_paths[0]
        else:
            guard = f"or {field_refs}"
        lines.append(f"{{{{- if {guard} -}}}}")
        lines.append(include_line)
        lines.append("{{- end -}}")
    return lines


def render_generated_template(groups: tuple[HelmSettingsGroup, ...]) -> str:
    lines = [_GENERATED_HEADER.rstrip()]

    lines.append('{{- define "base.externalService.env.ext" -}}')
    for group in groups:
        lines.extend(_emit_group_env_block(group, hooks=False))
    lines.append("{{- end -}}")
    lines.append("")

    lines.append('{{- define "base.externalService.hooks.env.ext" -}}')
    for group in groups:
        lines.extend(_emit_group_env_block(group, hooks=True))
    lines.append("{{- end -}}")
    lines.append("")

    lines.append(
        '{{- define "base.externalService.networkPolicy.cilium.egress.rules.ext" -}}'
    )
    for group in groups:
        lines.extend(_emit_egress_block(group))
    lines.append("{{- end -}}")
    lines.append("")

    lines.append(
        '{{- define "base.externalService.networkPolicy.cilium.egress.hasRules.ext" -}}'
    )
    lines.extend(_emit_has_rules_block(groups))
    lines.append("{{- end -}}")
    lines.append("")

    lines.append(
        '{{- define "base.externalService.networkPolicy.kubernetes.egress.validation.ext" -}}'
    )
    lines.append("{{- end -}}")
    lines.append("")

    lines.append(
        '{{- define "base.externalService.secretProvider.collectExtByVault.ext" -}}'
    )
    lines.extend(_emit_secret_provider_block(groups))
    lines.append("{{- end -}}")
    lines.append("")

    return "\n".join(lines)
