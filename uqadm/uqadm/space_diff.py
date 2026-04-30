"""Compare two space payloads as unified JSON diff."""

from __future__ import annotations

import json
import sys
from difflib import unified_diff
from pathlib import Path
from typing import Any

import click
from unique_sdk import Space

from uqadm.endpoint import EndpointParseError, parse_source_endpoint
from uqadm.env import config_for_slot

_VOLATILE_KEYS = frozenset({"createdAt", "updatedAt"})


def _strip_volatile(obj: Any) -> Any:
    """Recursively drop ``createdAt`` / ``updatedAt`` keys from mappings."""
    if isinstance(obj, dict):
        return {
            k: _strip_volatile(v) for k, v in obj.items() if k not in _VOLATILE_KEYS
        }
    if isinstance(obj, list):
        return [_strip_volatile(item) for item in obj]
    return obj


def _fetch_space(spec: str, cwd: Path | None) -> dict[str, Any]:
    slot, space_id = parse_source_endpoint(spec)
    cfg = config_for_slot(slot, cwd=cwd)
    row = Space.get_space(cfg.user_id, cfg.company_id, space_id)
    return dict(row)


def _canonical_lines(payload: dict[str, Any]) -> list[str]:
    text = json.dumps(payload, indent=2, sort_keys=True, default=str)
    return text.splitlines()


def cmd_diff(
    spec_a: str,
    spec_b: str,
    *,
    ignore_timestamps: bool,
    cwd: Path | None,
) -> None:
    """Load two spaces and print unified diff of canonical JSON."""
    try:
        a_raw = _fetch_space(spec_a, cwd=cwd)
        b_raw = _fetch_space(spec_b, cwd=cwd)
    except EndpointParseError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)
    except Exception as exc:
        click.echo(f"diff failed: {exc}", err=True)
        sys.exit(1)

    a_payload = _strip_volatile(a_raw) if ignore_timestamps else a_raw
    b_payload = _strip_volatile(b_raw) if ignore_timestamps else b_raw

    lines_a = _canonical_lines(a_payload)
    lines_b = _canonical_lines(b_payload)

    diff_lines = list(
        unified_diff(
            lines_a,
            lines_b,
            fromfile=f"a ({spec_a})",
            tofile=f"b ({spec_b})",
            lineterm="\n",
        )
    )
    if not diff_lines:
        click.echo("No differences.")
        return

    sys.stdout.writelines(diff_lines)
    sys.exit(1)
