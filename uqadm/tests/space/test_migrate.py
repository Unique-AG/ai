"""Tests for ``uqadm space migrate`` module-level helpers."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from uqadm.space.migrate import (
    build_create_params,
    build_module_updates_from_pairs,
    build_update_kwargs,
    cmd_migrate,
    mcp_servers_params_from_source,
)


def test_build_module_updates_from_pairs_returns_destination_module_id() -> None:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = [
        ({"name": "alpha"}, {"id": "mod_dst_1", "name": "alpha"}),
    ]
    out = build_module_updates_from_pairs(pairs)
    assert out == [{"moduleId": "mod_dst_1", "name": "alpha"}]


def test_build_module_updates_from_pairs_includes_present_optional_fields() -> None:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = [
        (
            {
                "name": "alpha",
                "description": "desc",
                "weight": 3,
                "configuration": {"k": "v"},
            },
            {"id": "mod_dst_1", "name": "alpha-dst"},
        ),
    ]
    out = build_module_updates_from_pairs(pairs)
    assert out == [
        {
            "moduleId": "mod_dst_1",
            "name": "alpha",
            "description": "desc",
            "weight": 3,
            "configuration": {"k": "v"},
        }
    ]


def test_build_module_updates_from_pairs_skips_none_optional_fields() -> None:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = [
        (
            {
                "name": "alpha",
                "description": None,
                "weight": None,
                "configuration": None,
            },
            {"id": "mod_dst_1"},
        ),
    ]
    out = build_module_updates_from_pairs(pairs)
    assert out == [{"moduleId": "mod_dst_1", "name": "alpha"}]


def test_build_module_updates_from_pairs_handles_multiple_entries() -> None:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = [
        ({"name": "a"}, {"id": "1"}),
        ({"name": "b", "weight": 7}, {"id": "2"}),
    ]
    out = build_module_updates_from_pairs(pairs)
    assert out == [
        {"moduleId": "1", "name": "a"},
        {"moduleId": "2", "name": "b", "weight": 7},
    ]


def test_build_module_updates_from_pairs_empty() -> None:
    assert build_module_updates_from_pairs([]) == []


# --- MCP servers (UN-27050) ---


def _attachments() -> list[dict[str, Any]]:
    return [
        {
            "id": "ams_1",
            "assistantId": "assistant_src",
            "name": "GitHub",
            "mcpServerId": "mcp_a",
            "isEnabled": True,
            "createdAt": "2026-10-01T00:00:00Z",
            "tools": [
                {"name": "search", "isEnabled": True},
                {"name": "delete", "isEnabled": False},
                {"name": "read", "isEnabled": True},
            ],
        },
        {
            "id": "ams_2",
            "mcpServerId": "mcp_b",
            "isEnabled": False,
            "tools": [{"name": "ask", "isEnabled": True}],
        },
        {"id": "ams_3", "mcpServerId": "mcp_c", "tools": []},
    ]


def test_mcp_servers_params_keep_only_enabled_tools_and_drop_export_fields() -> None:
    out = mcp_servers_params_from_source(_attachments())

    assert out[0] == {
        "mcpServerId": "mcp_a",
        "tools": [
            {"name": "search", "isEnabled": True},
            {"name": "read", "isEnabled": True},
        ],
    }


def test_mcp_servers_params_disabled_attachment_becomes_empty_tool_list() -> None:
    out = mcp_servers_params_from_source(_attachments())

    assert out[1] == {"mcpServerId": "mcp_b", "tools": []}
    assert out[2] == {"mcpServerId": "mcp_c", "tools": []}


@pytest.mark.parametrize(
    "value",
    [None, "x", {}, [None, "x", {"name": "no-id"}, {"mcpServerId": ""}]],
)
def test_mcp_servers_params_ignores_malformed_input(value: object) -> None:
    assert mcp_servers_params_from_source(value) == []


def test_build_params_leave_mcp_out_unless_asked() -> None:
    src = {
        "name": "S",
        "fallbackModule": "m",
        "modules": [],
        "assistantMcpServers": _attachments(),
    }

    assert "mcpServers" not in build_create_params(src)
    assert "mcpServers" not in build_update_kwargs(src)
    assert len(build_create_params(src, include_mcp_servers=True)["mcpServers"]) == 3
    assert len(build_update_kwargs(src, include_mcp_servers=True)["mcpServers"]) == 3


def test_build_params_skip_mcp_when_source_has_none() -> None:
    src = {"name": "S", "fallbackModule": "m", "modules": []}

    assert "mcpServers" not in build_create_params(src, include_mcp_servers=True)
    assert "mcpServers" not in build_update_kwargs(src, include_mcp_servers=True)


def _source_space() -> dict[str, Any]:
    return {
        "name": "Src",
        "fallbackModule": "m",
        "modules": [],
        "uiType": "SWAPPABLE_INTELLIGENCE",
        "assistantMcpServers": _attachments(),
    }


def _config(company: str, base: str) -> MagicMock:
    return MagicMock(user_id="u", company_id=company, api_base=base)


@patch("uqadm.space.migrate.config_for_slot")
def test_migrate_same_environment_sends_mcp_servers(mock_cfg: MagicMock) -> None:
    mock_cfg.return_value = _config("c1", "https://api.qa.example/public")
    with (
        patch("uqadm.space.migrate.Space.get_space", return_value=_source_space()),
        patch(
            "uqadm.space.migrate.Space.create_space", return_value={"id": "new"}
        ) as create,
    ):
        cmd_migrate("qa:space_src", "qa:", dry_run=False, with_knowledge=False)

    sent = create.call_args.kwargs
    assert [s["mcpServerId"] for s in sent["mcpServers"]] == [
        "mcp_a",
        "mcp_b",
        "mcp_c",
    ]
    assert sent["uiType"] == "SWAPPABLE_INTELLIGENCE"


@patch("uqadm.space.migrate.config_for_slot")
def test_migrate_cross_environment_skips_mcp_servers_with_warning(
    mock_cfg: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    mock_cfg.side_effect = [
        _config("c1", "https://api.qa.example/public"),
        _config("c2", "https://api.other.example/public"),
    ]
    with (
        patch("uqadm.space.migrate.Space.get_space", return_value=_source_space()),
        patch(
            "uqadm.space.migrate.Space.create_space", return_value={"id": "new"}
        ) as create,
    ):
        cmd_migrate("qa:space_src", "uat:", dry_run=False, with_knowledge=False)

    assert "mcpServers" not in create.call_args.kwargs
    assert "not portable across environments" in capsys.readouterr().err
