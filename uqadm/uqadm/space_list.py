"""List spaces via ``Space.get_spaces`` with pagination."""

from __future__ import annotations

import json
import sys
from typing import Any

import click
from unique_sdk import Space
from unique_sdk.cli.config import Config

from uqadm.auth_debug import echo_credential_debug_if_auth_failure

PAGE_SIZE = 1000


def fetch_all_spaces(
    user_id: str,
    company_id: str,
    *,
    name_filter: str | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    skip = 0
    while True:
        params: dict[str, Any] = {"skip": skip, "take": PAGE_SIZE}
        if name_filter:
            params["name"] = name_filter
        resp = Space.get_spaces(user_id, company_id, **params)
        chunk = list(resp.get("data") or [])
        rows.extend(chunk)
        if len(chunk) < PAGE_SIZE:
            break
        skip += PAGE_SIZE
    return rows


def print_spaces_table(rows: list[dict[str, Any]]) -> None:
    if not rows:
        click.echo("No spaces found.")
        return
    headers = ("id", "name", "uiType", "isPinned")
    widths = [len(h) for h in headers]
    lines: list[tuple[str, str, str, str]] = []
    for r in rows:
        line = (
            str(r.get("id", "")),
            str(r.get("name", "")),
            str(r.get("uiType", "")),
            str(r.get("isPinned", "")),
        )
        lines.append(line)
        widths[0] = max(widths[0], len(line[0]))
        widths[1] = max(widths[1], len(line[1]))
        widths[2] = max(widths[2], len(line[2]))
        widths[3] = max(widths[3], len(line[3]))

    fmt = "  ".join([f"{{:{w}}}" for w in widths])
    click.echo(fmt.format(*headers))
    click.echo(fmt.format(*["-" * w for w in widths]))
    for line in lines:
        click.echo(fmt.format(*line))


def print_spaces_json(rows: list[dict[str, Any]]) -> None:
    click.echo(json.dumps(rows, indent=2, default=str))


def cmd_list(
    cfg: Config,
    *,
    name_filter: str | None,
    as_json: bool,
) -> None:
    try:
        rows = fetch_all_spaces(cfg.user_id, cfg.company_id, name_filter=name_filter)
    except Exception as exc:
        click.echo(f"Error listing spaces: {exc}", err=True)
        echo_credential_debug_if_auth_failure(cfg, exc, label="space list")
        sys.exit(1)
    if as_json:
        print_spaces_json(rows)
    else:
        print_spaces_table(rows)
