"""Create or update a space from a local JSON/YAML snapshot file."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Literal

import click
import yaml
from unique_sdk import Space

from uqadm.auth_debug import echo_credential_debug_if_auth_failure
from uqadm.endpoint import EndpointParseError, parse_endpoint
from uqadm.env import config_for_slot
from uqadm.space_migrate import (
    build_create_params,
    build_update_kwargs,
    match_modules_by_name,
    sync_assistant_access,
)


def snapshot_format_for_path(path: Path) -> Literal["json", "yaml"]:
    """Return file format from ``path`` suffix, or raise ``ValueError`` if invalid."""
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix in (".yaml", ".yml"):
        return "yaml"
    raise ValueError(
        f"Snapshot file must end with .json, .yaml, or .yml (got: {path.name!r})."
    )


def load_space_snapshot(path: Path) -> dict[str, Any]:
    """Load a JSON or YAML space snapshot from disk."""
    fmt = snapshot_format_for_path(path)
    raw_text = path.read_text(encoding="utf-8")
    if fmt == "json":
        data = json.loads(raw_text)
    else:
        data = yaml.safe_load(raw_text)
    if not isinstance(data, dict):
        detail = type(data).__name__
        raise ValueError(f"Snapshot root must be a mapping (got {detail}).")
    return dict(data)


def _emit_snapshot_warnings(snapshot: dict[str, Any]) -> None:
    scope_rules = snapshot.get("scopeRules") or []
    if scope_rules:
        click.echo(
            f"Note: snapshot lists {len(scope_rules)} scope rule(s); "
            "these are not applied by upsert (same limitation as migrate).",
            err=True,
        )
    mcp = snapshot.get("assistantMcpServers") or []
    if mcp:
        click.echo(
            f"Warning: snapshot lists {len(mcp)} MCP server binding(s); "
            "these are not applied by upsert.",
            err=True,
        )


def _validate_snapshot(snapshot: dict[str, Any], *, creating: bool) -> None:
    if snapshot.get("name") is None:
        click.echo("Snapshot must include a non-null top-level 'name'.", err=True)
        sys.exit(2)
    if creating:
        if snapshot.get("fallbackModule") is None:
            click.echo(
                "Snapshot must include a non-null 'fallbackModule' for create "
                "(use slot-only --destination such as `2:` or `2`).",
                err=True,
            )
            sys.exit(2)


def cmd_upsert(
    spec: str,
    file_path: Path,
    *,
    dry_run: bool,
    cwd: Path | None,
) -> None:
    """Apply ``file_path`` snapshot to slot ``spec`` (create if no space id)."""
    try:
        slot, dst_space_id = parse_endpoint(spec)
    except EndpointParseError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)

    try:
        snapshot = load_space_snapshot(file_path)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)
    except json.JSONDecodeError as exc:
        click.echo(f"Invalid JSON in snapshot: {exc}", err=True)
        sys.exit(2)
    except yaml.YAMLError as exc:
        click.echo(f"Invalid YAML in snapshot: {exc}", err=True)
        sys.exit(2)

    creating = dst_space_id is None
    _validate_snapshot(snapshot, creating=creating)
    _emit_snapshot_warnings(snapshot)

    click.echo(f"Loading destination slot {slot!r} …")
    cfg = config_for_slot(slot, cwd=cwd)

    assistant_access = list(snapshot.get("assistantAccess") or [])

    if dst_space_id is None:
        create_params = build_create_params(snapshot)
        if dry_run:
            click.echo(
                f"Dry-run: would create_space with name="
                f"{create_params['name']!r} and "
                f"{len(create_params['modules'])} module(s)."
            )
            if assistant_access:
                click.echo(
                    f"Dry-run: would sync {len(assistant_access)} access entr(y/ies)."
                )
            return
        try:
            created = Space.create_space(
                cfg.user_id,
                cfg.company_id,
                **create_params,
            )
        except Exception as exc:
            click.echo(f"create_space failed: {exc}", err=True)
            echo_credential_debug_if_auth_failure(
                cfg, exc, label="space upsert create_space"
            )
            sys.exit(1)
        new_id = created["id"]
        click.echo(f"Created space {new_id}")
        sync_assistant_access(
            cfg.user_id,
            cfg.company_id,
            new_id,
            assistant_access,
            dry_run=dry_run,
            debug_cfg=cfg,
            credential_debug_label="space upsert add_space_access",
        )
        return

    try:
        dest_space = Space.get_space(
            cfg.user_id,
            cfg.company_id,
            dst_space_id,
        )
    except Exception as exc:
        click.echo(
            f"Error fetching destination space {dst_space_id!r}: {exc}",
            err=True,
        )
        echo_credential_debug_if_auth_failure(
            cfg, exc, label="space upsert destination get_space"
        )
        sys.exit(1)

    pairs, unmatched = match_modules_by_name(
        list(snapshot.get("modules") or []),
        list(dest_space.get("modules") or []),
    )
    if unmatched:
        click.echo(
            "Warning: no matching destination module for snapshot module(s) named: "
            + ", ".join(unmatched),
            err=True,
        )

    update_modules: list[dict[str, Any]] = []
    for sm, dm in pairs:
        um: dict[str, Any] = {"moduleId": dm["id"]}
        if sm.get("configuration") is not None:
            um["configuration"] = sm["configuration"]
        if sm.get("name") is not None:
            um["name"] = sm["name"]
        if sm.get("description") is not None:
            um["description"] = sm["description"]
        if sm.get("weight") is not None:
            um["weight"] = sm["weight"]
        update_modules.append(um)

    update_kw = build_update_kwargs(snapshot)
    if update_modules:
        update_kw["modules"] = update_modules

    if dry_run:
        click.echo(
            f"Dry-run: would update_space {dst_space_id!r} with fields "
            f"{sorted(update_kw.keys())!r}."
        )
        if assistant_access:
            click.echo(
                f"Dry-run: would merge access via add_space_access "
                f"({len(assistant_access)} entr(y/ies))."
            )
        return

    try:
        Space.update_space(
            cfg.user_id,
            cfg.company_id,
            dst_space_id,
            **update_kw,
        )
    except Exception as exc:
        click.echo(f"update_space failed: {exc}", err=True)
        echo_credential_debug_if_auth_failure(
            cfg, exc, label="space upsert update_space"
        )
        sys.exit(1)

    click.echo(f"Updated space {dst_space_id}")
    sync_assistant_access(
        cfg.user_id,
        cfg.company_id,
        dst_space_id,
        assistant_access,
        dry_run=dry_run,
        debug_cfg=cfg,
        credential_debug_label="space upsert add_space_access",
    )
