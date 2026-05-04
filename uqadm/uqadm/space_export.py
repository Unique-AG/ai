"""Export a single space snapshot as JSON or YAML."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Literal

import click
from unique_sdk import Space

from uqadm.auth_debug import echo_credential_debug_if_auth_failure
from uqadm.endpoint import EndpointParseError, parse_source_endpoint
from uqadm.env import config_for_slot
from uqadm.space_export_yaml import dump_space_snapshot_yaml


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
    spec: str,
    *,
    output: Path | None,
    cwd: Path | None,
) -> None:
    """Fetch ``Space.get_space`` and write canonical JSON or YAML to stdout or ``output``."""
    try:
        slot, space_id = parse_source_endpoint(spec)
    except EndpointParseError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)

    cfg = None
    try:
        cfg = config_for_slot(slot, cwd=cwd)
        payload = Space.get_space(
            cfg.user_id,
            cfg.company_id,
            space_id,
        )
    except Exception as exc:
        click.echo(f"export failed: {exc}", err=True)
        if cfg is not None:
            echo_credential_debug_if_auth_failure(cfg, exc, label="space export")
        sys.exit(1)

    normalized: dict[str, Any] = json.loads(
        json.dumps(payload, sort_keys=True, default=str)
    )

    if output is None:
        text = json.dumps(normalized, indent=2, sort_keys=True)
        click.echo(text)
        return

    try:
        fmt = export_format_for_output_path(output)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)

    if fmt == "json":
        text = json.dumps(normalized, indent=2, sort_keys=True)
    else:
        text = dump_space_snapshot_yaml(normalized).rstrip("\n")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text + "\n", encoding="utf-8")
