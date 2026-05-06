from __future__ import annotations

import pytest
from pydantic import BaseModel

from unique_mcp.meta.context_requirements import ContextRequirements
from unique_mcp.meta.keys import (
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


class _MockServer:
    def __init__(self, name: str) -> None:
        self.name = name


@pytest.mark.ai
def test_get_tool_config_returns_defaults() -> None:
    class MyConfig(BaseModel):
        value: int = 7

    dep = get_tool_config(MyConfig)
    config = dep.factory(server=_MockServer("test-server"))  # type: ignore[union-attr]
    assert isinstance(config, MyConfig)
    assert config.value == 7


@pytest.mark.ai
def test_get_tool_config_env_var_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    class MyConfig(BaseModel):
        value: int = 7

    env_key = _config_env_key("test-server", MyConfig)
    monkeypatch.setenv(env_key, '{"value": 42}')

    dep = get_tool_config(MyConfig)
    config = dep.factory(server=_MockServer("test-server"))  # type: ignore[union-attr]
    assert isinstance(config, MyConfig)
    assert config.value == 42
