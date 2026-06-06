from __future__ import annotations

from unittest import mock

import pytest
from pydantic import BaseModel

from unique_mcp.meta.context_requirements import ContextRequirements
from unique_mcp.meta.keys import (
    CONFIG_META_KEY,
    CONFIG_SCHEMA_META_KEY,
    CONTEXT_REQUIREMENTS_META_KEY,
    MetaKeys,
)
from unique_mcp.meta.part import merge_tool_meta
from unique_mcp.meta.rjsf import ConfigSchemaMeta
from unique_mcp.meta.tool import _config_env_key, get_tool_config


@pytest.mark.ai
def test_context_requirements_merge_into_meta_emits_canonical_key() -> None:
    reqs = ContextRequirements(
        required=[MetaKeys.USER_ID, MetaKeys.COMPANY_ID],
        optional=["unique.app/search/content-ids"],
    )
    meta: dict = {}
    reqs.merge_into_meta(meta)
    assert CONTEXT_REQUIREMENTS_META_KEY in meta
    payload = meta[CONTEXT_REQUIREMENTS_META_KEY]
    assert isinstance(payload, dict)
    assert payload["required"] == [MetaKeys.USER_ID, MetaKeys.COMPANY_ID]
    assert payload["optional"] == ["unique.app/search/content-ids"]
    assert payload["accepts_custom"] is False


@pytest.mark.ai
def test_merge_tool_meta_preserves_existing_keys() -> None:
    base: dict[str, object] = {
        "unique.app/icon": "data:image/svg",
        "other": 1,
    }
    reqs = ContextRequirements(required=[MetaKeys.USER_ID])
    merged = merge_tool_meta(base, reqs)

    assert merged["unique.app/icon"] == "data:image/svg"
    assert merged["other"] == 1
    assert CONTEXT_REQUIREMENTS_META_KEY in merged
    assert base == {"unique.app/icon": "data:image/svg", "other": 1}, (
        "merge_tool_meta must not mutate the input base dict"
    )


@pytest.mark.ai
def test_accepts_custom_flag_serialises() -> None:
    reqs = ContextRequirements(required=[MetaKeys.USER_ID], accepts_custom=True)
    meta: dict = {}
    reqs.merge_into_meta(meta)
    payload = meta[CONTEXT_REQUIREMENTS_META_KEY]
    assert isinstance(payload, dict)
    assert payload["accepts_custom"] is True


@pytest.mark.ai
def test_merge_tool_meta_with_none_base() -> None:
    reqs = ContextRequirements(required=[MetaKeys.USER_ID])
    merged = merge_tool_meta(None, reqs)
    assert list(merged.keys()) == [CONTEXT_REQUIREMENTS_META_KEY]


@pytest.mark.ai
def test_merge_tool_meta_zero_parts() -> None:
    merged = merge_tool_meta({"unique.app/icon": "x"})
    assert merged == {"unique.app/icon": "x"}


@pytest.mark.ai
def test_meta_key_class_attribute_matches_written_key() -> None:
    """_META_KEY on each class matches what merge_into_meta writes."""
    meta: dict = {}
    ContextRequirements().merge_into_meta(meta)
    assert ContextRequirements._META_KEY in meta

    class MyConfig(BaseModel):
        pass

    meta2: dict = {}
    ConfigSchemaMeta(MyConfig).merge_into_meta(meta2)
    assert ConfigSchemaMeta._META_KEY in meta2


@pytest.mark.ai
def test_config_schema_meta_emits_canonical_key() -> None:
    class MyConfig(BaseModel):
        value: int = 42

    meta: dict = {}
    ConfigSchemaMeta(MyConfig).merge_into_meta(meta)
    assert CONFIG_SCHEMA_META_KEY in meta
    payload = meta[CONFIG_SCHEMA_META_KEY]
    assert "json_schema" in payload
    assert "ui_schema" in payload
    assert payload["default_config"] == {"value": 42}


@pytest.mark.ai
def test_config_schema_meta_required_fields_raises_type_error() -> None:
    """Models with required fields are rejected immediately at construction time."""

    class StrictConfig(BaseModel):
        required_field: str  # no default — must be rejected

    with pytest.raises(TypeError, match="StrictConfig.*required_field"):
        ConfigSchemaMeta(StrictConfig)


@pytest.mark.ai
def test_config_schema_meta_uses_alias_generator_for_ui_schema_keys() -> None:
    from pydantic import ConfigDict
    from pydantic.alias_generators import to_camel

    class MyConfig(BaseModel):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
        my_field: int = 1

    meta: dict = {}
    ConfigSchemaMeta(MyConfig).merge_into_meta(meta)
    payload = meta[CONFIG_SCHEMA_META_KEY]
    assert payload["ui_schema"].get("myField") is not None
    assert "myField" in payload["json_schema"]["properties"]
    assert "myField" in payload["default_config"]


@pytest.mark.ai
def test_merge_tool_meta_with_multiple_parts() -> None:
    class MyConfig(BaseModel):
        value: int = 1

    reqs = ContextRequirements(required=[MetaKeys.USER_ID])
    schema_part = ConfigSchemaMeta(MyConfig)
    merged = merge_tool_meta({"unique.app/icon": "x"}, reqs, schema_part)
    assert "unique.app/icon" in merged
    assert CONTEXT_REQUIREMENTS_META_KEY in merged
    assert CONFIG_SCHEMA_META_KEY in merged


@pytest.mark.ai
def test_config_env_key_derivation() -> None:
    class SearchToolConfig(BaseModel):
        pass

    assert _config_env_key("mcp-search", SearchToolConfig) == (
        "UNIQUE_MCP_TOOL_MCP_SEARCH_SEARCH_TOOL_CONFIG"
    )


@pytest.mark.ai
def test_config_env_key_strips_config_suffix() -> None:
    class FooConfig(BaseModel):
        pass

    assert (
        _config_env_key("my-server", FooConfig)
        == "UNIQUE_MCP_TOOL_MY_SERVER_FOO_CONFIG"
    )


@pytest.mark.ai
def test_config_env_key_handles_spaces_in_server_name() -> None:
    class BarConfig(BaseModel):
        pass

    assert (
        _config_env_key("my server", BarConfig)
        == "UNIQUE_MCP_TOOL_MY_SERVER_BAR_CONFIG"
    )


@pytest.mark.ai
def test_config_env_key_handles_consecutive_separators() -> None:
    class BazConfig(BaseModel):
        pass

    assert (
        _config_env_key("my--server", BazConfig)
        == "UNIQUE_MCP_TOOL_MY_SERVER_BAZ_CONFIG"
    )


@pytest.mark.ai
def test_config_env_key_strips_non_ascii() -> None:
    class BazConfig(BaseModel):
        pass

    assert (
        _config_env_key("Knowledge Base Search 🚀", BazConfig)
        == "UNIQUE_MCP_TOOL_KNOWLEDGE_BASE_SEARCH_BAZ_CONFIG"
    )


class _MockServer:
    def __init__(self, name: str) -> None:
        self.name = name


def _call_dep(dep, server_name: str = "test-server"):
    """Call a get_tool_config resolver with a mocked FastMCP server."""
    with mock.patch(
        "unique_mcp.meta.tool.get_server", return_value=_MockServer(server_name)
    ):
        return dep()


@pytest.mark.ai
def test_get_tool_config_returns_defaults() -> None:
    class MyConfig(BaseModel):
        value: int = 7

    dep = get_tool_config(MyConfig)
    config = _call_dep(dep)
    assert isinstance(config, MyConfig)
    assert config.value == 7


@pytest.mark.ai
def test_get_tool_config_env_var_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    class MyConfig(BaseModel):
        value: int = 7

    env_key = _config_env_key("test-server", MyConfig)
    monkeypatch.setenv(env_key, '{"value": 42}')

    dep = get_tool_config(MyConfig)
    config = _call_dep(dep)
    assert isinstance(config, MyConfig)
    assert config.value == 42


@pytest.mark.ai
def test_get_tool_config_env_file_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    class MyConfig(BaseModel):
        value: int = 7

    env_key = _config_env_key("test-server", MyConfig)
    monkeypatch.delenv(env_key, raising=False)
    env_file = tmp_path / "unique_mcp.env"
    env_file.write_text(f'{env_key}={{"value": 88}}')
    monkeypatch.setenv("ENVIRONMENT_FILE_PATH", str(env_file))
    dep = get_tool_config(MyConfig)
    config = _call_dep(dep)

    assert isinstance(config, MyConfig)
    assert config.value == 88


@pytest.mark.ai
def test_get_tool_config_env_file_nonexistent_path_falls_back_to_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ENVIRONMENT_FILE_PATH pointing to a missing file should fall back to defaults."""

    class MyConfig(BaseModel):
        value: int = 7

    env_key = _config_env_key("test-server", MyConfig)
    monkeypatch.delenv(env_key, raising=False)
    monkeypatch.setenv("ENVIRONMENT_FILE_PATH", "/nonexistent/path/unique_mcp.env")
    dep = get_tool_config(MyConfig)
    config = _call_dep(dep)

    assert isinstance(config, MyConfig)
    assert config.value == 7  # default, env file was silently skipped


@pytest.mark.ai
def test_get_tool_config_meta_injection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Primary production path: config injected by host via _meta[CONFIG_META_KEY]."""

    class MyConfig(BaseModel):
        value: int = 7

    injected = {CONFIG_META_KEY: {"value": 99}}
    monkeypatch.setattr(
        "unique_mcp.unique_injectors.get_request_meta",
        lambda: injected,
    )

    dep = get_tool_config(MyConfig)
    config = _call_dep(dep)
    assert isinstance(config, MyConfig)
    assert config.value == 99


@pytest.mark.ai
def test_get_tool_config_meta_injection_json_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Host may inject config as a JSON string — both dict and str are accepted."""

    class MyConfig(BaseModel):
        value: int = 7

    import json

    injected = {CONFIG_META_KEY: json.dumps({"value": 55})}
    monkeypatch.setattr(
        "unique_mcp.unique_injectors.get_request_meta",
        lambda: injected,
    )

    dep = get_tool_config(MyConfig)
    config = _call_dep(dep)
    assert config.value == 55
