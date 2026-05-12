"""Tests for ``uqadm space_upsert`` command helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from uqadm.space_upsert import cmd_upsert


def _minimal_create_snapshot() -> dict[str, object]:
    return {
        "name": "NewSpace",
        "fallbackModule": "fallback_mod",
        "modules": [],
    }


def test_upsert_bad_snapshot_suffix_exits_2(tmp_path: Path) -> None:
    bad = tmp_path / "x.txt"
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        cmd_upsert("1:", bad, dry_run=False, cwd=None)
    assert exc_info.value.code == 2


def test_upsert_create_requires_fallback_module(tmp_path: Path) -> None:
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"name": "OnlyName"}), encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        cmd_upsert("1:", path, dry_run=True, cwd=None)
    assert exc_info.value.code == 2


@patch("uqadm.space_upsert.config_for_slot")
def test_upsert_create_dry_run_no_writes(
    mock_cfg: MagicMock,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_cfg.return_value = MagicMock(user_id="u", company_id="c")
    path = tmp_path / "snap.json"
    path.write_text(json.dumps(_minimal_create_snapshot()), encoding="utf-8")
    with patch("uqadm.space_upsert.Space.create_space") as mock_create:
        cmd_upsert("qa:", path, dry_run=True, cwd=None)
        mock_create.assert_not_called()
    out = capsys.readouterr().out
    assert "Dry-run: would create_space" in out


@patch("uqadm.space_upsert.config_for_slot")
def test_upsert_update_dry_run_no_writes(
    mock_cfg: MagicMock,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_cfg.return_value = MagicMock(user_id="u", company_id="c")
    path = tmp_path / "snap.json"
    path.write_text(
        json.dumps(
            {
                "name": "Updated",
                "modules": [{"name": "alpha", "configuration": {"k": 1}}],
            }
        ),
        encoding="utf-8",
    )
    dest_modules = [{"id": "mod_1", "name": "alpha"}]
    with patch(
        "uqadm.space_upsert.Space.get_space",
        return_value={"modules": dest_modules},
    ) as mock_get:
        with patch("uqadm.space_upsert.Space.update_space") as mock_up:
            cmd_upsert("qa:space_dst", path, dry_run=True, cwd=None)
            mock_up.assert_not_called()
        mock_get.assert_called_once_with("u", "c", "space_dst")
    out = capsys.readouterr().out
    assert "Dry-run: would update_space" in out
