"""Delete a single space via ``Space.delete_space``."""

from __future__ import annotations

import sys
import unicodedata
from typing import Any

import typer
from unique_sdk import Space
from unique_sdk.cli.config import Config

from uqadm.core.auth_debug import echo_credential_debug_if_auth_failure
from uqadm.core.endpoint import EndpointParseError, parse_bare_endpoint

_ALLOWED_WHITESPACE = {"\t", "\n", "\r"}


def sanitize_terminal_label(value: object) -> str:
    """Coerce ``value`` to ``str`` and strip C0/C1 control characters.

    Tabs, newlines and carriage returns are preserved; every other character
    in the C0 (U+0000–U+001F, U+007F) and C1 (U+0080–U+009F) ranges is
    replaced with a Unicode replacement marker.
    """
    text = value if isinstance(value, str) else str(value)
    return "".join(
        ch
        if ch in _ALLOWED_WHITESPACE or unicodedata.category(ch) != "Cc"
        else "\ufffd"
        for ch in text
    )


def _format_space_label(space: dict[str, Any]) -> str:
    name = sanitize_terminal_label(space.get("name") or "(unnamed)")
    ui_type = sanitize_terminal_label(space.get("uiType") or "?")
    return f"{name!r} (uiType={ui_type!r})"


def cmd_delete(
    raw_space_id: str,
    *,
    cfg: Config,
    yes: bool,
    dry_run: bool,
) -> None:
    """Delete the referenced space (with confirmation)."""
    try:
        space_id = parse_bare_endpoint(raw_space_id)
    except EndpointParseError as exc:
        typer.echo(str(exc), err=True)
        sys.exit(2)

    try:
        space = Space.get_space(cfg.user_id, cfg.company_id, space_id)
    except Exception as exc:
        typer.echo(f"Error fetching space {space_id!r}: {exc}", err=True)
        echo_credential_debug_if_auth_failure(cfg, exc, label="space delete get_space")
        sys.exit(1)

    label = _format_space_label(dict(space))

    if dry_run:
        typer.echo(f"Dry-run: would delete space {space_id} {label}.")
        return

    if not yes:
        confirmed = typer.confirm(
            f"Delete space {space_id} {label}?",
            default=False,
        )
        if not confirmed:
            typer.echo("Aborted.")
            return

    try:
        Space.delete_space(cfg.user_id, cfg.company_id, space_id)
    except Exception as exc:
        typer.echo(f"delete_space failed: {exc}", err=True)
        echo_credential_debug_if_auth_failure(
            cfg, exc, label="space delete delete_space"
        )
        sys.exit(1)

    typer.echo(f"Deleted space {space_id}")
