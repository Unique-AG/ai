"""Delete a single space via ``Space.delete_space``."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click
from unique_sdk import Space

from uqadm.auth_debug import echo_credential_debug_if_auth_failure
from uqadm.endpoint import EndpointParseError, parse_source_endpoint
from uqadm.env import config_for_slot


def _format_space_label(space: dict[str, Any]) -> str:
    name = space.get("name") or "(unnamed)"
    ui_type = space.get("uiType") or "?"
    return f"{name!r} (uiType={ui_type})"


def cmd_delete(
    spec: str,
    *,
    yes: bool,
    dry_run: bool,
    cwd: Path | None,
) -> None:
    """Resolve ``spec`` and delete the referenced space (with confirmation)."""
    try:
        slot, space_id = parse_source_endpoint(spec)
    except EndpointParseError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)

    cfg = config_for_slot(slot, cwd=cwd)

    try:
        space = Space.get_space(cfg.user_id, cfg.company_id, space_id)
    except Exception as exc:
        click.echo(f"Error fetching space {space_id!r}: {exc}", err=True)
        echo_credential_debug_if_auth_failure(cfg, exc, label="space delete get_space")
        sys.exit(1)

    label = _format_space_label(dict(space))

    if dry_run:
        click.echo(f"Dry-run: would delete space {space_id} {label}.")
        return

    if not yes:
        confirmed = click.confirm(
            f"Delete space {space_id} {label}?",
            default=False,
        )
        if not confirmed:
            click.echo("Aborted.")
            return

    try:
        Space.delete_space(cfg.user_id, cfg.company_id, space_id)
    except Exception as exc:
        click.echo(f"delete_space failed: {exc}", err=True)
        echo_credential_debug_if_auth_failure(
            cfg, exc, label="space delete delete_space"
        )
        sys.exit(1)

    click.echo(f"Deleted space {space_id}")
