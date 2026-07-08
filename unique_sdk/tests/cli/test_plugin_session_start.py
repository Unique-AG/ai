"""Tests for the Unique CLI Claude plugin SessionStart hook."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SESSION_START = (
    REPO_ROOT
    / "unique_sdk"
    / "claude-marketplace"
    / "plugins"
    / "unique-cli"
    / "scripts"
    / "session-start.sh"
)


def test_session_start_writes_config_and_publishes_path(tmp_path: Path) -> None:
    """The hook persists credentials and exports UNIQUE_CONFIG_PATH."""
    plugin_root = tmp_path / "plugin"
    bin_dir = plugin_root / "bin"
    bin_dir.mkdir(parents=True)
    calls_file = tmp_path / "calls.log"
    fake_cli = bin_dir / "unique-cli"
    fake_cli.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> "{calls_file}"
case "$1" in
  write-config)
    printf '{{}}\\n' > "$3"
    ;;
esac
""",
        encoding="utf-8",
    )
    fake_cli.chmod(0o755)

    env = {
        **os.environ,
        "HOME": str(tmp_path / "home"),
        "CLAUDE_PLUGIN_ROOT": str(plugin_root),
        "CLAUDE_PLUGIN_DATA": str(tmp_path / "data"),
        "CLAUDE_ENV_FILE": str(tmp_path / "env-file"),
    }

    result = subprocess.run(
        ["bash", str(SESSION_START)],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    config_file = tmp_path / "data" / "config.json"
    assert config_file.exists()
    calls = calls_file.read_text(encoding="utf-8").splitlines()
    assert calls == [f"write-config --out {config_file}"]
    env_file = (tmp_path / "env-file").read_text(encoding="utf-8")
    assert env_file == f'export UNIQUE_CONFIG_PATH="{config_file}"\n'


def test_session_start_is_a_no_op_outside_claude(tmp_path: Path) -> None:
    """Without the Claude plugin environment the hook exits quietly."""
    result = subprocess.run(
        ["bash", str(SESSION_START)],
        env={**os.environ, "CLAUDE_PLUGIN_ROOT": "", "CLAUDE_PLUGIN_DATA": ""},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout == ""
