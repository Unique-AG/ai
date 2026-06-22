from __future__ import annotations

import json
from pathlib import Path

from unique_search_proxy_client.web.helm.generator import (
    check_artifacts,
    generate_artifacts,
    generated_groups_tuple,
)
from unique_search_proxy_client.web.helm.generator.introspect import (
    env_var_name,
    iter_helm_fields,
)
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
        "vertexaiAgent",
    }


def test_generated_schema_contains_all_provider_blocks() -> None:
    schema = json.loads((CHART_DIR / "values.additional.schema.json").read_text())
    properties = schema["properties"]
    for group in helm_generated_groups():
        assert group.helm_key in properties
        block = properties[group.helm_key]
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


def test_stale_google_template_is_absent() -> None:
    assert not (CHART_DIR / "templates" / "_google.tpl").exists()
