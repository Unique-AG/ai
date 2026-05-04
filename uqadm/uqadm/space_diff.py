"""Compare two space payloads as unified JSON diff."""

from __future__ import annotations

import json
import sys
from difflib import unified_diff
from pathlib import Path
from typing import Any

import click
from unique_sdk import Space
from unique_sdk.cli.config import Config

from uqadm.auth_debug import echo_credential_debug_if_auth_failure
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
    cfg_a: Config | None = None
    try:
        slot_a, space_id_a = parse_source_endpoint(spec_a)
        cfg_a = config_for_slot(slot_a, cwd=cwd)
        a_raw = dict(
            Space.get_space(cfg_a.user_id, cfg_a.company_id, space_id_a),
        )
    except EndpointParseError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)
    except Exception as exc:
        click.echo(f"diff failed fetching first space ({spec_a!r}): {exc}", err=True)
        if cfg_a is not None:
            echo_credential_debug_if_auth_failure(
                cfg_a, exc, label=f"space diff side a ({spec_a!r})"
            )
        sys.exit(1)

    cfg_b: Config | None = None
    try:
        slot_b, space_id_b = parse_source_endpoint(spec_b)
        cfg_b = config_for_slot(slot_b, cwd=cwd)
        b_raw = dict(
            Space.get_space(cfg_b.user_id, cfg_b.company_id, space_id_b),
        )
    except EndpointParseError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)
    except Exception as exc:
        click.echo(f"diff failed fetching second space ({spec_b!r}): {exc}", err=True)
        if cfg_b is not None:
            echo_credential_debug_if_auth_failure(
                cfg_b, exc, label=f"space diff side b ({spec_b!r})"
            )
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
