"""Export a single space snapshot as JSON or YAML."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Literal

import typer
from unique_sdk import Space
from unique_sdk.cli.config import Config

from uqadm.core.auth_debug import echo_credential_debug_if_auth_failure
from uqadm.core.endpoint import EndpointParseError, parse_bare_endpoint
from uqadm.space.export_yaml import dump_space_snapshot_yaml


def export_format_for_output_path(path: Path) -> Literal["json", "yaml"]:
    """Return file format from ``path`` suffix, or raise ``ValueError`` if invalid."""
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix in (".yaml", ".yml"):
        return "yaml"
    raise ValueError(
        f"Output file must end with .json, .yaml, or .yml (got: {path.name!r})."
    )


def cmd_export(
    raw_space_id: str,
    *,
    cfg: Config,
    output: Path | None,
) -> None:
    """Fetch ``Space.get_space`` and write canonical JSON or YAML to stdout or ``output``."""
    try:
        space_id = parse_bare_endpoint(raw_space_id)
    except EndpointParseError as exc:
        typer.echo(str(exc), err=True)
        sys.exit(2)

    try:
        payload = Space.get_space(
            cfg.user_id,
            cfg.company_id,
            space_id,
        )
    except Exception as exc:
        typer.echo(f"export failed: {exc}", err=True)
        echo_credential_debug_if_auth_failure(cfg, exc, label="space export")
        sys.exit(1)

    normalized: dict[str, Any] = json.loads(
        json.dumps(payload, sort_keys=True, default=str)
    )

    if output is None:
        text = json.dumps(normalized, indent=2, sort_keys=True)
        typer.echo(text)
        return

    try:
        fmt = export_format_for_output_path(output)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        sys.exit(2)

    if fmt == "json":
        text = json.dumps(normalized, indent=2, sort_keys=True)
    else:
        text = dump_space_snapshot_yaml(normalized).rstrip("\n")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text + "\n", encoding="utf-8")
