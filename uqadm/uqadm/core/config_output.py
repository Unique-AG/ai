"""Emit an ingestion config to stdout or a JSON/YAML file."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer
import yaml

from uqadm.core.payload_files import snapshot_format_for_path


def write_config_document(config: dict[str, Any], output: Path | None) -> None:
    """Write ``config`` to ``output``, or print it as JSON on stdout.

    Keys are sorted and non-serializable values stringified so that repeated
    dumps of the same folder diff cleanly and always round-trip back through
    ``uqadm kb ingestion set``. The format follows the ``output`` suffix.
    """
    normalized: dict[str, Any] = json.loads(
        json.dumps(config, sort_keys=True, default=str)
    )
    if output is None:
        typer.echo(json.dumps(normalized, indent=2, sort_keys=True))
        return
    try:
        fmt = snapshot_format_for_path(output)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        sys.exit(2)
    if fmt == "json":
        text = json.dumps(normalized, indent=2, sort_keys=True)
    else:
        text = yaml.safe_dump(normalized, default_flow_style=False, sort_keys=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text.rstrip("\n") + "\n", encoding="utf-8")
