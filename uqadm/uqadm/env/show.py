"""Show resolved credentials for a slot (API key redacted)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from uqadm.core.auth_debug import format_credential_debug_lines
from uqadm.core.cli_auth import load_config_or_exit, resolve_slot_or_exit


def cmd_env_show(
    slot: Optional[str],
    *,
    cwd: Path | None,
) -> None:
    """Print resolved credential values for ``slot`` (API key redacted)."""
    resolved = resolve_slot_or_exit(slot)
    cfg = load_config_or_exit(resolved, cwd)

    for line in format_credential_debug_lines(cfg, label=f"slot {resolved!r}"):
        typer.echo(line)
