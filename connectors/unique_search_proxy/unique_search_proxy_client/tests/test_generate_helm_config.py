from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic_settings import BaseSettings

from unique_search_proxy_client.web.helm.generator import (
    check_artifacts,
    generate_artifacts,
    generated_groups_tuple,
)
from unique_search_proxy_client.web.helm.generator.introspect import (
    env_var_name,
    iter_helm_fields,
)
from unique_search_proxy_client.web.helm.metadata import assign_field_sections
from unique_search_proxy_client.web.helm.registry import helm_generated_groups

CHART_DIR = Path(__file__).resolve().parents[1] / "deploy" / "helm-chart"


def test_all_registry_groups_have_helm_keys() -> None:
    keys = {group.helm_key for group in helm_generated_groups()}
    assert keys == {
        "bingAgent",
        "braveSearch",
        "firecrawl",
        "googleSearch",
        "httpClient",
        "jina",
        "perplexitySearch",
        "tavily",
        "urlSafety",
        "vertexaiAgent",
    }


def test_provider_groups_are_gated_but_always_on_config_is_not() -> None:
    """The helm gate is opt-out: providers gated, always-on config not.

    This is the chart-only ``enabled`` gate, distinct from a group's real runtime
    activation field (e.g. urlSafety.enabled).
    """
    gated = {g.helm_key: g.gated for g in helm_generated_groups()}
    assert gated["httpClient"] is False
    assert gated["urlSafety"] is False
    provider_keys = set(gated) - {"httpClient", "urlSafety"}
    assert provider_keys, "expected at least one gated provider group"
    assert all(gated[key] for key in provider_keys)


def test_generated_schema_contains_all_provider_blocks() -> None:
    schema = json.loads((CHART_DIR / "values.additional.schema.json").read_text())
    properties = schema["properties"]
    for group in helm_generated_groups():
        assert group.helm_key in properties
        block = properties[group.helm_key]
        if not group.gated:
            # Non-gated groups get no synthetic ``enabled`` helm gate. A real
            # activation field (urlSafety.enabled) still appears; httpClient has
            # none.
            if group.helm_key == "urlSafety":
                assert block["properties"]["enabled"]["default"] is True
                assert "connection" not in block["properties"]
                assert "redirects" in block["properties"]
                assert "network" in block["properties"]
            else:
                assert "enabled" not in block["properties"]
                assert "connection" in block["properties"]
            continue
        assert block["properties"]["enabled"]["default"] is False
        assert "connection" in block["properties"]
        required_fields = [
            field
            for field in iter_helm_fields(group.model, env_prefix=group.env_prefix)
            if field.required_when_enabled
        ]
        if required_fields:
            assert "allOf" in block


def test_generated_template_env_vars_match_pydantic_names() -> None:
    template = (CHART_DIR / "templates" / "_providers.tpl").read_text()
    for group in generated_groups_tuple():
        assert group.helm_key is not None
        for field in iter_helm_fields(group.model, env_prefix=group.env_prefix):
            if not field.emit_in_template:
                continue
            assert field.env_var in template
            assert env_var_name(field.python_name, group.env_prefix) == field.env_var


def test_generated_values_yaml_has_provider_markers() -> None:
    values = (CHART_DIR / "values.yaml").read_text()
    assert "# @helm-gen:begin providers" in values
    assert "# @helm-gen:end providers" in values
    assert "googleSearch:" in values
    assert "httpClient:" in values
    assert "urlSafety:" in values


def test_http_client_values_yaml_has_tuning_section() -> None:
    values = (CHART_DIR / "values.yaml").read_text()
    http_client_index = values.index("httpClient:")
    http_client_block = values[
        http_client_index : values.index("\n\n", http_client_index)
    ]
    assert "  tuning:" in http_client_block
    assert "    poolTimeoutSeconds:" in http_client_block


def test_http_client_values_yaml_has_no_enabled_toggle() -> None:
    """httpClient has no runtime ``enabled`` field, so it must not emit one.

    Emitting ``enabled: false`` while the template injects env vars regardless
    would be misleading; emitting it as a real gate silently drops proxy config.
    """
    values = (CHART_DIR / "values.yaml").read_text()
    http_client_index = values.index("httpClient:")
    http_client_block = values[
        http_client_index : values.index("\n\n", http_client_index)
    ]
    assert "enabled:" not in http_client_block


def test_http_client_env_injection_is_not_enabled_gated() -> None:
    """Proxy env vars must render from their own fields, not a synthetic flag.

    Regression for overlays that set ``httpClient.connection.*`` (proxy host /
    secrets) without ``httpClient.enabled: true`` and silently deployed with no
    ``HTTP_CLIENT_*`` env vars.
    """
    template = (CHART_DIR / "templates" / "_providers.tpl").read_text()
    assert "and .Values.httpClient .Values.httpClient.enabled" not in template
    assert "and .ctx.Values.httpClient .ctx.Values.httpClient.enabled" not in template
    # The non-secret proxy defaults are always emitted (no enclosing gate).
    assert "HTTP_CLIENT_PROXY_AUTH_MODE" in template
    # Proxy secrets are collected whenever configured, gated on the fields
    # themselves rather than on a meaningless ``enabled`` toggle.
    assert (
        "{{- if or .ctx.Values.httpClient.connection.proxyUsername "
        ".ctx.Values.httpClient.connection.proxyPassword -}}"
    ) in template


def test_url_safety_lists_are_overridable_in_chart() -> None:
    """SSRF guardrail lists must be overlay-tunable for customer-managed tenants.

    They render as real (replaceable) values.yaml lists, get array schemas, and
    inject as JSON-encoded env vars that pydantic-settings parses back to lists.
    """
    values = (CHART_DIR / "values.yaml").read_text()
    url_safety_index = values.index("urlSafety:")
    url_safety_block = values[url_safety_index : values.index("\n\n", url_safety_index)]
    assert "    allowedSchemes:\n      - http\n      - https" in url_safety_block
    assert "    metadataHosts:\n" in url_safety_block

    schema = json.loads((CHART_DIR / "values.additional.schema.json").read_text())
    network = schema["properties"]["urlSafety"]["properties"]["network"]["properties"]
    for key in ("allowedSchemes", "localhostHosts", "metadataHosts"):
        assert network[key]["type"] == "array"
        assert network[key]["items"] == {"type": "string"}

    template = (CHART_DIR / "templates" / "_providers.tpl").read_text()
    assert (
        "value: {{ .Values.urlSafety.network.allowedSchemes | toJson | quote }}"
        in template
    )


def test_assign_field_sections_injects_section_metadata() -> None:
    class SampleSettings(BaseSettings):
        host: str = "localhost"
        timeout: int = 30

    assign_field_sections(SampleSettings, {"tuning": ["timeout"]})
    fields = iter_helm_fields(SampleSettings, env_prefix="SAMPLE_")
    by_name = {field.python_name: field for field in fields}
    assert by_name["host"].section == "connection"
    assert by_name["timeout"].section == "tuning"


def test_assign_field_sections_rejects_unknown_field() -> None:
    class SampleSettings(BaseSettings):
        host: str = "localhost"

    with pytest.raises(ValueError, match="unknown fields"):
        assign_field_sections(SampleSettings, {"tuning": ["missing"]})


def test_assign_field_sections_rejects_duplicate_assignment() -> None:
    class SampleSettings(BaseSettings):
        host: str = "localhost"
        timeout: int = 30

    with pytest.raises(ValueError, match="assigned to two sections"):
        assign_field_sections(
            SampleSettings,
            {"tuning": ["timeout"], "other": ["timeout"]},
        )


def test_check_artifacts_passes_on_committed_files() -> None:
    drift = check_artifacts(CHART_DIR)
    assert drift == []


def test_generate_artifacts_is_deterministic() -> None:
    first = generate_artifacts(CHART_DIR)
    second = generate_artifacts(CHART_DIR)
    assert first == second


def test_google_template_preserves_required_engine_id_guard() -> None:
    template = (CHART_DIR / "templates" / "_providers.tpl").read_text()
    assert 'required "googleSearch.connection.engineId is required' in template
    assert "GOOGLE_SEARCH_API_KEY" in template
    assert "toFQDNs:" in template
    assert "or and .Values" not in template
    assert (
        "(list .ctx.Values.httpClient.connection.proxyUsername "
        ".ctx.Values.httpClient.connection.proxyPassword)"
    ) in template
    assert ".Values.httpClient.tuning.poolTimeoutSeconds" in template


def test_stale_google_template_is_absent() -> None:
    assert not (CHART_DIR / "templates" / "_google.tpl").exists()
