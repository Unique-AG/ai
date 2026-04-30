"""Export a single space snapshot as JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from unique_sdk import Space

from uqadm.endpoint import EndpointParseError, parse_source_endpoint
from uqadm.env import config_for_slot


def cmd_export(
    spec: str,
    *,
    output: Path | None,
    cwd: Path | None,
) -> None:
    """Fetch ``Space.get_space`` and write canonical JSON to stdout or ``output``."""
    try:
        slot, space_id = parse_source_endpoint(spec)
    except EndpointParseError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)

    try:
        cfg = config_for_slot(slot, cwd=cwd)
        payload = Space.get_space(
            cfg.user_id,
            cfg.company_id,
            space_id,
        )
    except Exception as exc:
        click.echo(f"export failed: {exc}", err=True)
        sys.exit(1)

    text = json.dumps(payload, indent=2, sort_keys=True, default=str)
    if output is None:
        click.echo(text)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
