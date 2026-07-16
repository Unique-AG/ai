"""CLI integration tests for new ``uqadm space`` commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from uqadm.cli import app


def _runner() -> CliRunner:
    return CliRunner()


@patch("uqadm.space.cmd_space_access_grant")
@patch("uqadm.core.cli_auth.config_for_slot")
@patch("uqadm.core.cli_auth.resolve_slot", return_value="qa")
def test_space_access_grant_cli(
    mock_resolve: MagicMock,
    mock_cfg: MagicMock,
    mock_grant: MagicMock,
) -> None:
    mock_cfg.return_value = MagicMock()
    result = _runner().invoke(
        app,
        [
            "space",
            "access-grant",
            "asst_abc",
            "--group",
            "g1",
            "--type",
            "MANAGE",
            "--slot",
            "qa",
        ],
    )
    assert result.exit_code == 0
    mock_grant.assert_called_once()
    kw = mock_grant.call_args.kwargs
    assert kw["space_id"] == "asst_abc"
    assert kw["group_ids"] == ("g1",)
    assert kw["access_type"] == "MANAGE"


@patch("uqadm.space.cmd_space_access_grant")
@patch("uqadm.core.cli_auth.config_for_slot")
@patch("uqadm.core.cli_auth.resolve_slot", return_value="qa")
def test_space_access_grant_invalid_space_id_exits_2(
    mock_resolve: MagicMock,
    mock_cfg: MagicMock,
    mock_grant: MagicMock,
) -> None:
    mock_cfg.return_value = MagicMock()
    result = _runner().invoke(
        app,
        ["space", "access-grant", "1:", "--group", "g1", "--slot", "qa"],
    )
    assert result.exit_code == 2
    mock_grant.assert_not_called()


@patch("uqadm.space.cmd_space_ingestion_set")
@patch("uqadm.core.cli_auth.config_for_slot")
@patch("uqadm.core.cli_auth.resolve_slot", return_value="qa")
def test_space_ingestion_set_cli(
    mock_resolve: MagicMock,
    mock_cfg: MagicMock,
    mock_set: MagicMock,
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "ing.yaml"
    cfg_file.write_text("chunkStrategy: fixed\n", encoding="utf-8")
    mock_cfg.return_value = MagicMock()
    result = _runner().invoke(
        app,
        [
            "space",
            "ingestion-set",
            "asst_xyz",
            str(cfg_file),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    mock_set.assert_called_once()
    kw = mock_set.call_args.kwargs
    assert kw["space_id"] == "asst_xyz"
    assert kw["dry_run"] is True


@patch("uqadm.space.cmd_space_ingestion_set")
@patch("uqadm.core.cli_auth.config_for_slot")
@patch("uqadm.core.cli_auth.resolve_slot", return_value="qa")
def test_space_ingestion_set_invalid_space_id_exits_2(
    mock_resolve: MagicMock,
    mock_cfg: MagicMock,
    mock_set: MagicMock,
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "ing.json"
    cfg_file.write_text("{}", encoding="utf-8")
    mock_cfg.return_value = MagicMock()
    result = _runner().invoke(
        app,
        ["space", "ingestion-set", "", str(cfg_file)],
    )
    assert result.exit_code == 2
    mock_set.assert_not_called()
