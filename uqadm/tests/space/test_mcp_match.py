"""Tests for matching snapshot MCP bindings onto a destination company."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from uqadm.space.mcp_match import resolve_mcp_attachments
from uqadm.space.upsert import cmd_upsert


def _server(
    server_id: str,
    name: str,
    tools: list[str],
    *,
    restricted: bool = False,
    allowed: list[str] | None = None,
) -> dict[str, object]:
    return {
        "id": server_id,
        "name": name,
        "isSpaceRestricted": restricted,
        "allowedSpaceIds": allowed or [],
        "tools": [{"name": tool} for tool in tools],
    }


def _binding(
    server_id: str,
    name: str,
    tools: list[dict[str, object]] | None = None,
    *,
    enabled: bool = True,
    include_tools: bool = True,
) -> dict[str, object]:
    binding: dict[str, object] = {
        "name": name,
        "mcpServerId": server_id,
        "isEnabled": enabled,
    }
    if include_tools:
        binding["tools"] = tools if tools is not None else []
    return binding


def test_id_match_sends_tools_that_exist_on_the_destination() -> None:
    attachments, warnings = resolve_mcp_attachments(
        [
            _binding(
                "mcp_src",
                "GitHub",
                [
                    {"name": "search_issues", "isEnabled": True},
                    {"name": "search_code", "isEnabled": False},
                    {"name": "missing_tool", "isEnabled": True},
                ],
            )
        ],
        [_server("mcp_src", "GitHub", ["search_issues", "search_code"])],
        match="id",
        destination_space_id="assistant_dst",
    )

    assert attachments == [
        {
            "mcpServerId": "mcp_src",
            "tools": [{"name": "search_issues", "isEnabled": True}],
        }
    ]
    assert warnings == [
        "Warning: MCP server GitHub (mcp_src): "
        "snapshot tool 'missing_tool' is not on the destination server"
    ]


def test_unknown_id_is_dropped_and_omits_mcp_servers() -> None:
    attachments, warnings = resolve_mcp_attachments(
        [_binding("mcp_src", "GitHub", [{"name": "search_issues", "isEnabled": True}])],
        [_server("mcp_other", "GitHub", ["search_issues"])],
        match="id",
        destination_space_id="assistant_dst",
    )

    assert attachments is None
    assert warnings == [
        "Warning: dropping MCP server GitHub (mcp_src): "
        "no server with this id on the destination"
    ]


def test_unique_name_rewrites_to_the_destination_id() -> None:
    attachments, warnings = resolve_mcp_attachments(
        [
            _binding(
                "mcp_src",
                "GitHub MCP",
                [{"name": "search_issues", "isEnabled": True}],
            )
        ],
        [_server("mcp_dst", "GitHub MCP", ["search_issues"])],
        match="name",
        destination_space_id="assistant_dst",
    )

    assert attachments == [
        {
            "mcpServerId": "mcp_dst",
            "tools": [{"name": "search_issues", "isEnabled": True}],
        }
    ]
    assert warnings == []


def test_ambiguous_name_is_dropped() -> None:
    attachments, warnings = resolve_mcp_attachments(
        [
            _binding(
                "mcp_src", "mcp.atlassian.com", [{"name": "search", "isEnabled": True}]
            )
        ],
        [
            _server("mcp_a", "mcp.atlassian.com", ["search"]),
            _server("mcp_b", "mcp.atlassian.com", ["search"]),
        ],
        match="name",
        destination_space_id="assistant_dst",
    )

    assert attachments is None
    assert (
        "more than one destination server is named 'mcp.atlassian.com'" in warnings[0]
    )


def test_empty_enabled_tools_are_not_sent_as_an_empty_list() -> None:
    attachments, warnings = resolve_mcp_attachments(
        [_binding("mcp_src", "GitHub", [])],
        [_server("mcp_src", "GitHub", ["search_issues"])],
        match="id",
        destination_space_id="assistant_dst",
    )

    assert attachments is None
    assert "snapshot has no enabled tools" in warnings[0]


def test_missing_tool_list_omits_tools_and_warns() -> None:
    attachments, warnings = resolve_mcp_attachments(
        [_binding("mcp_src", "GitHub", include_tools=False)],
        [_server("mcp_src", "GitHub", ["search_issues"])],
        match="id",
        destination_space_id="assistant_dst",
    )

    assert attachments == [{"mcpServerId": "mcp_src"}]
    assert "every callable tool" in warnings[0]
    assert "tools" not in attachments[0]


def test_no_remaining_tool_names_drops_the_server() -> None:
    attachments, warnings = resolve_mcp_attachments(
        [_binding("mcp_src", "GitHub", [{"name": "gone", "isEnabled": True}])],
        [_server("mcp_src", "GitHub", ["search_issues"])],
        match="id",
        destination_space_id="assistant_dst",
    )

    assert attachments is None
    assert any("gone" in warning for warning in warnings)
    assert any("none of the enabled snapshot tools" in warning for warning in warnings)


def test_space_restricted_server_is_skipped_on_create() -> None:
    attachments, warnings = resolve_mcp_attachments(
        [_binding("mcp_src", "GitHub", [{"name": "search_issues", "isEnabled": True}])],
        [
            _server(
                "mcp_src",
                "GitHub",
                ["search_issues"],
                restricted=True,
                allowed=["assistant_dst"],
            )
        ],
        match="id",
        destination_space_id=None,
    )

    assert attachments is None
    assert "cannot be attached while creating a space" in warnings[0]


def test_space_restricted_server_is_kept_when_the_space_is_allowed() -> None:
    attachments, _warnings = resolve_mcp_attachments(
        [_binding("mcp_src", "GitHub", [{"name": "search_issues", "isEnabled": True}])],
        [
            _server(
                "mcp_src",
                "GitHub",
                ["search_issues"],
                restricted=True,
                allowed=["assistant_dst"],
            )
        ],
        match="id",
        destination_space_id="assistant_dst",
    )

    assert attachments == [
        {
            "mcpServerId": "mcp_src",
            "tools": [{"name": "search_issues", "isEnabled": True}],
        }
    ]


def test_disabled_source_binding_is_dropped() -> None:
    attachments, warnings = resolve_mcp_attachments(
        [
            _binding(
                "mcp_src",
                "GitHub",
                [{"name": "search_issues", "isEnabled": True}],
                enabled=False,
            )
        ],
        [_server("mcp_src", "GitHub", ["search_issues"])],
        match="id",
        destination_space_id="assistant_dst",
    )

    assert attachments is None
    assert "source binding is disabled" in warnings[0]


@patch("uqadm.space.upsert.config_for_slot")
@patch("uqadm.space.mcp_match.MCP.list_servers")
def test_upsert_dry_run_prints_name_match_and_does_not_create(
    mock_list: MagicMock,
    mock_cfg: MagicMock,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_cfg.return_value = MagicMock(user_id="u", company_id="c")
    mock_list.return_value = {
        "mcpServers": [_server("mcp_dst", "GitHub MCP", ["search_issues"])]
    }
    path = tmp_path / "snap.json"
    path.write_text(
        json.dumps(
            {
                "name": "NewSpace",
                "fallbackModule": "fallback_mod",
                "modules": [],
                "assistantMcpServers": [
                    _binding(
                        "mcp_src",
                        "GitHub MCP",
                        [{"name": "search_issues", "isEnabled": True}],
                    ),
                    _binding(
                        "mcp_missing",
                        "Office",
                        [{"name": "mail", "isEnabled": True}],
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )

    with patch("uqadm.space.upsert.Space.create_space") as mock_create:
        cmd_upsert(
            path,
            "qa",
            target_space_id=None,
            dry_run=True,
            cwd=None,
            mcp_match="name",
        )
        mock_create.assert_not_called()

    mock_list.assert_called_once_with("u", "c")
    captured = capsys.readouterr()
    assert (
        'Dry-run: would send mcpServers=[{"mcpServerId":"mcp_dst",'
        '"tools":[{"name":"search_issues","isEnabled":true}]}]'
    ) in captured.out
    assert "dropping MCP server Office (mcp_missing)" in captured.err
    assert "no server named 'Office'" in captured.err
