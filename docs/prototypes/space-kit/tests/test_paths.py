from pathlib import Path

import pytest

from space_kit.base import JsonObject, SpaceKitError
from space_kit.paths import (
    Assignment,
    flatten,
    get_path,
    parse_assignment,
    parse_value,
    set_path,
)

pytestmark = pytest.mark.ai


def _config() -> JsonObject:
    return {
        "claude": {"effort": "auto", "model": "m"},
        "tools": [
            {"name": "WebSearch", "isEnabled": True},
            {
                "name": "search",
                "isEnabled": True,
                "configuration": {"mcpTool": True, "mcpServerId": "mcp_a"},
            },
            {
                "name": "search",
                "isEnabled": False,
                "configuration": {"mcpTool": True, "mcpServerId": "mcp_b"},
            },
        ],
    }


def test_set_path_returns_a_changed_copy_and_keeps_the_input() -> None:
    original = _config()

    changed = set_path(
        data=original,
        assignment=Assignment(path="claude.effort", value="low"),
        allow_new_keys=False,
    )

    assert get_path(data=changed, path="claude.effort") == "low"
    assert get_path(data=original, path="claude.effort") == "auto"


def test_set_path_refuses_a_typo_and_lists_known_keys() -> None:
    with pytest.raises(SpaceKitError, match=r"claude\.efort does not exist.*effort"):
        _ = set_path(
            data=_config(),
            assignment=Assignment(path="claude.efort", value="low"),
            allow_new_keys=False,
        )


def test_set_path_adds_a_key_only_when_allowed() -> None:
    changed = set_path(
        data=_config(),
        assignment=Assignment(path="claude.newKey.inner", value=1),
        allow_new_keys=True,
    )

    assert get_path(data=changed, path="claude.newKey.inner") == 1


def test_selector_addresses_a_tool_by_name() -> None:
    changed = set_path(
        data=_config(),
        assignment=Assignment(path="tools[WebSearch].isEnabled", value=False),
        allow_new_keys=False,
    )

    assert get_path(data=changed, path="tools[WebSearch].isEnabled") is False


def test_selector_with_server_disambiguates_shared_tool_names() -> None:
    assert get_path(data=_config(), path="tools[search@mcp_b].isEnabled") is False
    with pytest.raises(SpaceKitError, match="matches 2 items"):
        _ = get_path(data=_config(), path="tools[search].isEnabled")


def test_flatten_keys_shared_tool_names_by_server() -> None:
    flat = flatten(data=_config())

    assert flat["claude.effort"] == "auto"
    assert flat["tools[WebSearch].isEnabled"] is True
    assert flat["tools[search@mcp_a].isEnabled"] is True
    assert flat["tools[search@mcp_b].isEnabled"] is False


def test_parse_value_reads_json_text_and_files(tmp_path: Path) -> None:
    _ = (tmp_path / "prompt.md").write_text("Be brief.", encoding="utf-8")

    assert parse_value(text="500", base_dir=tmp_path) == 500
    assert parse_value(text="true", base_dir=tmp_path) is True
    assert parse_value(text="low", base_dir=tmp_path) == "low"
    assert parse_value(text='"true"', base_dir=tmp_path) == "true"
    assert parse_value(text="@file:prompt.md", base_dir=tmp_path) == "Be brief."


def test_parse_assignment_requires_path_equals_value(tmp_path: Path) -> None:
    assert parse_assignment(text="a.b=1", base_dir=tmp_path).value == 1
    with pytest.raises(SpaceKitError, match="expected path=value"):
        _ = parse_assignment(text="a.b", base_dir=tmp_path)
