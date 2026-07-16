"""CLI integration tests for ``uqadm kb`` Typer commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from uqadm.cli import app
from uqadm.core.env import MissingSlotEnvFileError
from uqadm.core.slot import MissingDefaultSlotError


def _runner() -> CliRunner:
    return CliRunner()


@patch("uqadm.kb.cmd_mkdir")
@patch("uqadm.core.cli_auth.config_for_slot")
@patch("uqadm.core.cli_auth.resolve_slot", return_value="qa")
def test_kb_mkdir_cli_invokes_helper(
    mock_resolve: MagicMock,
    mock_cfg: MagicMock,
    mock_mkdir: MagicMock,
) -> None:
    mock_cfg.return_value = MagicMock(user_id="u1", company_id="c1")
    result = _runner().invoke(app, ["kb", "mkdir", "/A", "/B", "--slot", "qa"])
    assert result.exit_code == 0
    mock_resolve.assert_called_once_with("qa")
    mock_cfg.assert_called_once()
    mock_mkdir.assert_called_once()
    call_kw = mock_mkdir.call_args.kwargs
    assert call_kw["extra_paths"] == ["/A", "/B"]


@patch("uqadm.core.cli_auth.resolve_slot", side_effect=MissingDefaultSlotError("no default"))
def test_kb_mkdir_missing_default_slot_exits_2(mock_resolve: MagicMock) -> None:
    result = _runner().invoke(app, ["kb", "mkdir", "/A"])
    assert result.exit_code == 2
    assert "no default" in (result.output or result.stderr or "")


@patch("uqadm.core.cli_auth.config_for_slot", side_effect=MissingSlotEnvFileError("missing env"))
@patch("uqadm.core.cli_auth.resolve_slot", return_value="qa")
def test_kb_mkdir_missing_env_exits_2(
    mock_resolve: MagicMock, mock_cfg: MagicMock
) -> None:
    result = _runner().invoke(app, ["kb", "mkdir", "/A", "--slot", "qa"])
    assert result.exit_code == 2
    assert "missing env" in (result.output or result.stderr or "")


@patch("uqadm.kb.cmd_sync")
@patch("uqadm.core.cli_auth.config_for_slot")
@patch("uqadm.core.cli_auth.resolve_slot", return_value="qa")
def test_kb_sync_cli_invokes_helper(
    mock_resolve: MagicMock,
    mock_cfg: MagicMock,
    mock_sync: MagicMock,
    tmp_path: Path,
) -> None:
    mock_cfg.return_value = MagicMock(user_id="u1", company_id="c1")
    result = _runner().invoke(
        app,
        ["kb", "sync", str(tmp_path), "--folder-path", "/X", "-r", "--dry-run"],
    )
    assert result.exit_code == 0
    mock_sync.assert_called_once()
    kw = mock_sync.call_args.kwargs
    assert kw["local_dir"] == tmp_path
    assert kw["folder_path"] == "/X"
    assert kw["scope_id"] is None
    assert kw["recursive"] is True
    assert kw["dry_run"] is True
    assert kw["versioning"] is True


@patch("uqadm.kb.cmd_sync")
@patch("uqadm.core.cli_auth.config_for_slot")
@patch("uqadm.core.cli_auth.resolve_slot", return_value="qa")
def test_kb_sync_no_version_cli(
    mock_resolve: MagicMock,
    mock_cfg: MagicMock,
    mock_sync: MagicMock,
    tmp_path: Path,
) -> None:
    mock_cfg.return_value = MagicMock(user_id="u1", company_id="c1")
    result = _runner().invoke(
        app,
        [
            "kb",
            "sync",
            str(tmp_path),
            "--folder-path",
            "/X",
            "--no-version",
        ],
    )
    assert result.exit_code == 0
    mock_sync.assert_called_once()
    assert mock_sync.call_args.kwargs["versioning"] is False


@patch("uqadm.kb.cmd_download")
@patch("uqadm.core.cli_auth.config_for_slot")
@patch("uqadm.core.cli_auth.resolve_slot", return_value="qa")
def test_kb_download_cli_invokes_helper(
    mock_resolve: MagicMock,
    mock_cfg: MagicMock,
    mock_download: MagicMock,
    tmp_path: Path,
) -> None:
    mock_cfg.return_value = MagicMock(user_id="u1", company_id="c1")
    out_dir = tmp_path / "out"
    result = _runner().invoke(
        app,
        ["kb", "download", str(out_dir), "--scope-id", "scope_x", "-r", "--dry-run"],
    )
    assert result.exit_code == 0
    mock_download.assert_called_once()
    kw = mock_download.call_args.kwargs
    assert kw["local_dir"] == out_dir
    assert kw["folder_path"] is None
    assert kw["scope_id"] == "scope_x"
    assert kw["recursive"] is True
    assert kw["dry_run"] is True


@patch("uqadm.kb.cmd_download")
@patch("uqadm.core.cli_auth.config_for_slot")
@patch("uqadm.core.cli_auth.resolve_slot", return_value="qa")
def test_kb_download_rejects_existing_file_target(
    mock_resolve: MagicMock,
    mock_cfg: MagicMock,
    mock_download: MagicMock,
    tmp_path: Path,
) -> None:
    existing_file = tmp_path / "out.txt"
    existing_file.write_text("data", encoding="utf-8")
    result = _runner().invoke(
        app,
        ["kb", "download", str(existing_file), "--scope-id", "scope_x"],
    )
    assert result.exit_code == 2
    mock_download.assert_not_called()


@patch("uqadm.kb.cmd_rm")
@patch("uqadm.core.cli_auth.config_for_slot")
@patch("uqadm.core.cli_auth.resolve_slot", return_value="qa")
def test_kb_rm_cli_invokes_helper(
    mock_resolve: MagicMock,
    mock_cfg: MagicMock,
    mock_rm: MagicMock,
) -> None:
    mock_cfg.return_value = MagicMock(user_id="u1", company_id="c1")
    result = _runner().invoke(
        app,
        ["kb", "rm", "--scope-id", "scope_x", "-r", "--dry-run", "--file", "a.txt"],
    )
    assert result.exit_code == 0
    mock_rm.assert_called_once()
    kw = mock_rm.call_args.kwargs
    assert kw["folder_path"] is None
    assert kw["scope_id"] == "scope_x"
    assert kw["files"] == ("a.txt",)
    assert kw["recursive"] is True
    assert kw["dry_run"] is True
    assert kw["assume_yes"] is False


@patch("uqadm.kb.cmd_access_grant")
@patch("uqadm.core.cli_auth.config_for_slot")
@patch("uqadm.core.cli_auth.resolve_slot", return_value="qa")
def test_kb_access_grant_cli(
    mock_resolve: MagicMock,
    mock_cfg: MagicMock,
    mock_grant: MagicMock,
) -> None:
    mock_cfg.return_value = MagicMock()
    result = _runner().invoke(
        app,
        [
            "kb",
            "access",
            "grant",
            "--folder-path",
            "/HR",
            "--group",
            "g1",
            "--permission",
            "WRITE",
        ],
    )
    assert result.exit_code == 0
    mock_grant.assert_called_once()
    kw = mock_grant.call_args.kwargs
    assert kw["folder_path"] == "/HR"
    assert kw["group_ids"] == ("g1",)
    assert kw["permission"] == "WRITE"


@patch("uqadm.kb.cmd_ingestion_set")
@patch("uqadm.core.cli_auth.config_for_slot")
@patch("uqadm.core.cli_auth.resolve_slot", return_value="qa")
def test_kb_ingestion_set_cli(
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
        [
            "kb",
            "ingestion",
            "set",
            str(cfg_file),
            "--scope-id",
            "scope_x",
            "--no-subfolders",
        ],
    )
    assert result.exit_code == 0
    mock_set.assert_called_once()
    kw = mock_set.call_args.kwargs
    assert kw["scope_id"] == "scope_x"
    assert kw["apply_to_subfolders"] is False
