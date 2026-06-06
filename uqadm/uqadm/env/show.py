"""Show resolved credentials for a slot (API key redacted)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from uqadm.core.auth_debug import format_credential_debug_lines
from uqadm.core.env import MissingSlotEnvFileError, config_for_slot
from uqadm.core.slot import MissingDefaultSlotError, resolve_slot


def cmd_env_show(
    slot: Optional[str],
    *,
    cwd: Path | None,
) -> None:
    """Print resolved credential values for ``slot`` (API key redacted)."""
    try:
        resolved = resolve_slot(slot)
    except MissingDefaultSlotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2)

    try:
        cfg = config_for_slot(resolved, cwd=cwd)
    except MissingSlotEnvFileError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2)

    for line in format_credential_debug_lines(cfg, label=f"slot {resolved!r}"):
        typer.echo(line)
