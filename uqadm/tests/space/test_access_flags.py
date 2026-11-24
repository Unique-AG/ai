"""Tests for access/MCP/scope-rule handling in space upsert, migrate, export, diff."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from uqadm.space.diff import cmd_diff
from uqadm.space.export import cmd_export
from uqadm.space.migrate import (
    SnapshotError,
    build_create_params,
    build_update_kwargs,
    cmd_migrate,
    mcp_server_params_from_source,
    resolve_access_entries,
    strip_access_keys,
)
from uqadm.space.upsert import cmd_upsert

_ACCESS = [
    {"id": "acc_1", "entityId": "grp_1", "entityType": "GROUP", "type": "USE"},
]
_MCP = [
    {
        "id": "bind_1",
        "name": "Jira",
        "assistantId": "space_src",
        "mcpServerId": "mcp_1",
        "isEnabled": True,
        "tools": [{"name": "search", "isEnabled": True}],
        "createdAt": "t",
        "updatedAt": "t",
    }
]


def _space(**extra: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "space_src",
        "name": "Space",
        "fallbackModule": "fallback",
        "modules": [{"id": "m_src", "name": "alpha", "configuration": {"k": 1}}],
        "assistantAccess": list(_ACCESS),
        "access": ["grp_1"],
        "scopeRules": [{"id": "r1", "title": "rule", "rule": {}}],
        "assistantMcpServers": list(_MCP),
    }
    base.update(extra)
    return base


def _cfg(company: str = "c", base: str = "https://api.example/public") -> MagicMock:
    return MagicMock(user_id="u", company_id=company, api_base=base)


_DST_MCP_SERVERS = {
    "mcpServers": [
        {
            "id": "mcp_1",
            "name": "Jira",
            "isSpaceRestricted": False,
            "allowedSpaceIds": [],
            "tools": [{"name": "search"}],
        }
    ]
}


def _patch_list_servers(servers: dict[str, Any] | None = None) -> Any:
    return patch(
        "uqadm.space.mcp_match.MCP.list_servers",
        return_value=servers if servers is not None else _DST_MCP_SERVERS,
    )


# --- helpers ---


def test_mcp_server_params_strip_source_only_fields() -> None:
    assert mcp_server_params_from_source(_MCP) == [
        {"mcpServerId": "mcp_1", "tools": [{"name": "search", "isEnabled": True}]}
    ]


def test_mcp_server_params_disabled_binding_maps_to_empty_tools() -> None:
    entries = [{"mcpServerId": "mcp_2", "isEnabled": False, "tools": []}]
    assert mcp_server_params_from_source(entries) == [
        {"mcpServerId": "mcp_2", "tools": []}
    ]


def test_mcp_server_params_enabled_without_tools_omits_tools() -> None:
    entries = [{"mcpServerId": "mcp_3", "isEnabled": True}]
    assert mcp_server_params_from_source(entries) == [{"mcpServerId": "mcp_3"}]


def test_mcp_server_params_none_is_empty() -> None:
    assert mcp_server_params_from_source(None) == []


@pytest.mark.parametrize(
    "entries",
    [
        "not-a-list",
        [{"name": "no server id"}],
        ["bad"],
        [{"mcpServerId": "m", "isEnabled": True, "tools": 1}],
        [{"mcpServerId": "m", "isEnabled": True, "tools": [{"isEnabled": True}]}],
        [{"mcpServerId": "m", "isEnabled": True, "tools": ["search"]}],
        # non-string ids / names
        [{"mcpServerId": 42, "isEnabled": True}],
        [{"mcpServerId": "", "isEnabled": True}],
        [{"mcpServerId": "m", "tools": [{"name": 7, "isEnabled": True}]}],
        # non-boolean states must never be coerced (bool("false") is True)
        [{"mcpServerId": "m", "tools": [{"name": "s", "isEnabled": "false"}]}],
        [{"mcpServerId": "m", "tools": [{"name": "s"}]}],
        [{"mcpServerId": "m", "isEnabled": "false"}],
        [{"mcpServerId": "m", "isEnabled": None}],
    ],
)
def test_mcp_server_params_reject_malformed_input(entries: Any) -> None:
    # Invalid selections must fail loudly, never widen to "enable all tools".
    with pytest.raises(SnapshotError):
        mcp_server_params_from_source(entries)


def test_mcp_server_params_preserves_literal_false_tool_state() -> None:
    entries = [
        {
            "mcpServerId": "m",
            "isEnabled": True,
            "tools": [
                {"name": "a", "isEnabled": False},
                {"name": "b", "isEnabled": True},
            ],
        }
    ]
    assert mcp_server_params_from_source(entries) == [
        {
            "mcpServerId": "m",
            "tools": [
                {"name": "a", "isEnabled": False},
                {"name": "b", "isEnabled": True},
            ],
        }
    ]


def test_mcp_server_params_missing_binding_state_defaults_to_enabled() -> None:
    assert mcp_server_params_from_source([{"mcpServerId": "m"}]) == [
        {"mcpServerId": "m"}
    ]


def test_mcp_server_params_enabled_with_empty_tools_omits_tools() -> None:
    entries = [{"mcpServerId": "m", "isEnabled": True, "tools": []}]
    assert mcp_server_params_from_source(entries) == [{"mcpServerId": "m"}]


def test_resolve_access_entries_no_access_does_not_parse_field(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert resolve_access_entries(1, no_access=True) == []
    assert "--no-access set" in capsys.readouterr().err


def test_resolve_access_entries_rejects_non_list_without_no_access() -> None:
    with pytest.raises(SnapshotError):
        resolve_access_entries(1, no_access=False)
    assert resolve_access_entries(None, no_access=False) == []


def test_build_params_include_mcp_only_when_requested() -> None:
    src = _space()
    assert "mcpServers" not in build_create_params(src)
    assert "mcpServers" not in build_update_kwargs(src)
    assert (
        build_create_params(src, include_mcp=True)["mcpServers"][0]["mcpServerId"]
        == "mcp_1"
    )
    assert (
        build_update_kwargs(src, include_mcp=True)["mcpServers"][0]["mcpServerId"]
        == "mcp_1"
    )


def test_strip_access_keys() -> None:
    out = strip_access_keys(_space())
    assert "assistantAccess" not in out
    assert "access" not in out
    assert out["name"] == "Space"


# --- upsert ---


def _write_snapshot(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "snap.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.mark.parametrize("no_access", [False, True])
@patch("uqadm.space.upsert.config_for_slot")
def test_upsert_update_access_sync_respects_no_access(
    mock_cfg: MagicMock, tmp_path: Path, no_access: bool
) -> None:
    mock_cfg.return_value = _cfg()
    path = _write_snapshot(tmp_path, _space())
    with (
        patch(
            "uqadm.space.upsert.Space.get_space",
            return_value={"modules": [{"id": "m_dst", "name": "alpha"}]},
        ),
        patch("uqadm.space.upsert.Space.update_space") as mock_update,
        patch("uqadm.space.migrate.Space.add_space_access") as mock_add,
    ):
        cmd_upsert(
            path,
            "qa",
            target_space_id="space_dst",
            dry_run=False,
            cwd=None,
            no_access=no_access,
        )
    mock_update.assert_called_once()
    assert "mcpServers" not in mock_update.call_args.kwargs
    if no_access:
        mock_add.assert_not_called()
    else:
        mock_add.assert_called_once()
        assert mock_add.call_args.kwargs["access"] == [
            {"entityId": "grp_1", "entityType": "GROUP", "type": "USE"}
        ]


@patch("uqadm.space.upsert.config_for_slot")
def test_upsert_create_no_access_skips_access(
    mock_cfg: MagicMock, tmp_path: Path
) -> None:
    mock_cfg.return_value = _cfg()
    path = _write_snapshot(tmp_path, _space())
    with (
        patch(
            "uqadm.space.upsert.Space.create_space", return_value={"id": "new"}
        ) as mock_create,
        patch("uqadm.space.migrate.Space.add_space_access") as mock_add,
    ):
        cmd_upsert(
            path, "qa", target_space_id=None, dry_run=False, cwd=None, no_access=True
        )
    mock_create.assert_called_once()
    mock_add.assert_not_called()


@patch("uqadm.space.upsert.config_for_slot")
def test_upsert_dry_run_no_access_omits_access_line_and_warns(
    mock_cfg: MagicMock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    mock_cfg.return_value = _cfg()
    path = _write_snapshot(tmp_path, _space())
    with patch(
        "uqadm.space.upsert.Space.get_space",
        return_value={"modules": [{"id": "m_dst", "name": "alpha"}]},
    ):
        cmd_upsert(
            path,
            "qa",
            target_space_id="space_dst",
            dry_run=True,
            cwd=None,
            no_access=True,
        )
    captured = capsys.readouterr()
    assert "would merge access" not in captured.out
    assert "--no-access set; skipping 1 access" in captured.err
    assert "1 scope rule(s) are NOT applied" in captured.err
    assert "pass --with-mcp-servers" in captured.err


@patch("uqadm.space.upsert.config_for_slot")
def test_upsert_with_mcp_servers_sends_bindings(
    mock_cfg: MagicMock, tmp_path: Path
) -> None:
    mock_cfg.return_value = _cfg()
    path = _write_snapshot(tmp_path, _space())
    with (
        patch(
            "uqadm.space.upsert.Space.get_space",
            return_value={"modules": [{"id": "m_dst", "name": "alpha"}]},
        ),
        patch("uqadm.space.upsert.Space.update_space") as mock_update,
        patch("uqadm.space.migrate.Space.add_space_access"),
        _patch_list_servers(),
    ):
        cmd_upsert(
            path,
            "qa",
            target_space_id="space_dst",
            dry_run=False,
            cwd=None,
            with_mcp_servers=True,
        )
    assert mock_update.call_args.kwargs["mcpServers"] == [
        {"mcpServerId": "mcp_1", "tools": [{"name": "search", "isEnabled": True}]}
    ]


# --- migrate ---


def _run_migrate(
    *,
    dst_cfg: MagicMock,
    no_access: bool = False,
    with_mcp_servers: bool = False,
    dst_mcp_servers: dict[str, Any] | None = None,
) -> tuple[MagicMock, MagicMock]:
    src_cfg = _cfg()

    def _get_space(user_id: str, company_id: str, space_id: str) -> dict[str, Any]:
        if space_id == "space_src":
            return _space()
        return {"id": "space_dst", "modules": [{"id": "m_dst", "name": "alpha"}]}

    with (
        patch(
            "uqadm.space.migrate.config_for_slot",
            side_effect=lambda slot, cwd=None: src_cfg if slot == "a" else dst_cfg,
        ),
        patch("uqadm.space.migrate.Space.get_space", side_effect=_get_space),
        patch("uqadm.space.migrate.Space.update_space") as mock_update,
        patch("uqadm.space.migrate.Space.add_space_access") as mock_add,
        _patch_list_servers(dst_mcp_servers),
    ):
        cmd_migrate(
            "a:space_src",
            "b:space_dst",
            dry_run=False,
            with_knowledge=False,
            no_access=no_access,
            with_mcp_servers=with_mcp_servers,
        )
    return mock_update, mock_add


def test_migrate_update_no_access_skips_access() -> None:
    mock_update, mock_add = _run_migrate(dst_cfg=_cfg(), no_access=True)
    mock_update.assert_called_once()
    mock_add.assert_not_called()


def test_migrate_update_default_merges_access() -> None:
    _, mock_add = _run_migrate(dst_cfg=_cfg())
    mock_add.assert_called_once()


def test_migrate_with_mcp_servers_same_env_sends_bindings() -> None:
    mock_update, _ = _run_migrate(dst_cfg=_cfg(), with_mcp_servers=True)
    assert mock_update.call_args.kwargs["mcpServers"][0]["mcpServerId"] == "mcp_1"


def test_migrate_with_mcp_servers_cross_env_attaches_matched_servers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_update, _ = _run_migrate(dst_cfg=_cfg(company="other"), with_mcp_servers=True)
    assert mock_update.call_args.kwargs["mcpServers"] == [
        {"mcpServerId": "mcp_1", "tools": [{"name": "search", "isEnabled": True}]}
    ]
    assert "1 scope rule(s) are NOT applied" in capsys.readouterr().err


def test_migrate_with_mcp_servers_drops_unmatched_and_omits_mcp_servers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_update, _ = _run_migrate(
        dst_cfg=_cfg(company="other"),
        with_mcp_servers=True,
        dst_mcp_servers={"mcpServers": []},
    )
    assert "mcpServers" not in mock_update.call_args.kwargs
    assert "dropping MCP server Jira (mcp_1)" in capsys.readouterr().err


# --- export ---


def test_export_no_access_strips_access_keys(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch("uqadm.space.export.Space.get_space", return_value=_space()):
        cmd_export("space_src", cfg=_cfg(), output=None, no_access=True)
    payload = json.loads(capsys.readouterr().out)
    assert "assistantAccess" not in payload
    assert "access" not in payload
    assert payload["scopeRules"]


def test_export_default_keeps_access(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("uqadm.space.export.Space.get_space", return_value=_space()):
        cmd_export("space_src", cfg=_cfg(), output=None)
    payload = json.loads(capsys.readouterr().out)
    assert payload["assistantAccess"][0]["entityId"] == "grp_1"


# --- diff ---


@pytest.mark.parametrize("strict", [False, True])
def test_diff_ignore_access_reports_no_differences(
    strict: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    a = _space()
    b = _space(
        assistantAccess=[
            {"id": "x", "entityId": "grp_9", "entityType": "GROUP", "type": "MANAGE"}
        ],
        access=["grp_9"],
    )
    with (
        patch("uqadm.space.diff.config_for_slot", return_value=_cfg()),
        patch("uqadm.space.diff.Space.get_space", side_effect=[a, b]),
    ):
        cmd_diff(
            "a:space_src",
            "b:space_src",
            strict=strict,
            output_format="unified",
            cwd=None,
            ignore_access=True,
        )
    assert "No differences." in capsys.readouterr().out


def test_diff_without_ignore_access_detects_acl_drift() -> None:
    a = _space()
    b = _space(access=["grp_9"])
    with (
        patch("uqadm.space.diff.config_for_slot", return_value=_cfg()),
        patch("uqadm.space.diff.Space.get_space", side_effect=[a, b]),
        pytest.raises(SystemExit) as exc_info,
    ):
        cmd_diff(
            "a:space_src",
            "b:space_src",
            strict=False,
            output_format="unified",
            cwd=None,
        )
    assert exc_info.value.code == 1


@patch("uqadm.space.upsert.config_for_slot")
def test_upsert_malformed_mcp_exits_2_before_any_write(
    mock_cfg: MagicMock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    mock_cfg.return_value = _cfg()
    bad = _space(
        assistantMcpServers=[{"mcpServerId": "m", "isEnabled": True, "tools": 1}]
    )
    path = _write_snapshot(tmp_path, bad)
    with (
        patch(
            "uqadm.space.upsert.Space.get_space",
            return_value={"modules": [{"id": "m_dst", "name": "alpha"}]},
        ),
        patch("uqadm.space.upsert.Space.update_space") as mock_update,
        pytest.raises(SystemExit) as exc_info,
    ):
        cmd_upsert(
            path,
            "qa",
            target_space_id="space_dst",
            dry_run=False,
            cwd=None,
            with_mcp_servers=True,
        )
    assert exc_info.value.code == 2
    mock_update.assert_not_called()
    assert "Invalid snapshot" in capsys.readouterr().err


@patch("uqadm.space.upsert.config_for_slot")
def test_upsert_no_access_ignores_malformed_access_field(
    mock_cfg: MagicMock, tmp_path: Path
) -> None:
    mock_cfg.return_value = _cfg()
    path = _write_snapshot(tmp_path, _space(assistantAccess=1))
    with (
        patch(
            "uqadm.space.upsert.Space.get_space",
            return_value={"modules": [{"id": "m_dst", "name": "alpha"}]},
        ),
        patch("uqadm.space.upsert.Space.update_space") as mock_update,
        patch("uqadm.space.migrate.Space.add_space_access") as mock_add,
    ):
        cmd_upsert(
            path,
            "qa",
            target_space_id="space_dst",
            dry_run=False,
            cwd=None,
            no_access=True,
        )
    mock_update.assert_called_once()
    mock_add.assert_not_called()


@patch("uqadm.space.upsert.config_for_slot")
def test_upsert_create_dry_run_reports_mcp_plan(
    mock_cfg: MagicMock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    mock_cfg.return_value = _cfg()
    path = _write_snapshot(tmp_path, _space())
    with _patch_list_servers():
        cmd_upsert(
            path,
            "qa",
            target_space_id=None,
            dry_run=True,
            cwd=None,
            with_mcp_servers=True,
        )
    err = capsys.readouterr().err
    assert "Dry-run: would apply 1 MCP server binding(s)" in err


def test_migrate_without_flag_does_not_list_destination_mcp_servers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch("uqadm.space.mcp_match.MCP.list_servers") as mock_list:
        mock_update, _ = _run_migrate(dst_cfg=_cfg(company="other"))
    mock_list.assert_not_called()
    assert "mcpServers" not in mock_update.call_args.kwargs
    assert "pass --with-mcp-servers" in capsys.readouterr().err
