"""Tests for ``uqadm install`` bootstrap command."""

from __future__ import annotations

from pathlib import Path

import pytest

from uqadm.install import _RC_BEGIN, _detect_shell, _patch_rc, _rc_already_patched


def test_rc_already_patched_false_for_empty_file(tmp_path: Path) -> None:
    rc = tmp_path / ".zshrc"
    rc.write_text("# existing content\n", encoding="utf-8")
    assert _rc_already_patched(rc) is False


def test_rc_already_patched_true_when_marker_present(tmp_path: Path) -> None:
    rc = tmp_path / ".zshrc"
    rc.write_text(f"# stuff\n{_RC_BEGIN}\nexport UQADM_HOME=...\n", encoding="utf-8")
    assert _rc_already_patched(rc) is True


def test_patch_rc_appends_block(tmp_path: Path) -> None:
    rc = tmp_path / ".zshrc"
    rc.write_text("# existing\n", encoding="utf-8")
    home = tmp_path / ".uqadm"
    _patch_rc(rc, home, dry_run=False)
    content = rc.read_text()
    assert _RC_BEGIN in content
    assert str(home) in content


def test_patch_rc_idempotent(tmp_path: Path) -> None:
    rc = tmp_path / ".zshrc"
    rc.write_text("# existing\n", encoding="utf-8")
    home = tmp_path / ".uqadm"
    _patch_rc(rc, home, dry_run=False)
    first_content = rc.read_text()
    _patch_rc(rc, home, dry_run=False)
    assert rc.read_text() == first_content


def test_patch_rc_dry_run_does_not_write(tmp_path: Path) -> None:
    rc = tmp_path / ".zshrc"
    rc.write_text("# existing\n", encoding="utf-8")
    home = tmp_path / ".uqadm"
    _patch_rc(rc, home, dry_run=True)
    assert _RC_BEGIN not in rc.read_text()


def test_detect_shell_reads_shell_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHELL", "/bin/zsh")
    assert _detect_shell() == "zsh"
    monkeypatch.setenv("SHELL", "/usr/bin/bash")
    assert _detect_shell() == "bash"
