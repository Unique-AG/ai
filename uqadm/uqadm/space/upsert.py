"""Create or update a space from a local JSON/YAML snapshot file."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer
import yaml
from unique_sdk import Space

from uqadm.core.auth_debug import echo_credential_debug_if_auth_failure
from uqadm.core.env import config_for_slot
from uqadm.core.payload_files import load_json_or_yaml_mapping
from uqadm.space.migrate import (
    SnapshotError,
    build_create_params,
    build_module_updates_from_pairs,
    build_update_kwargs,
    echo_mcp_plan,
    list_len,
    match_modules_by_name,
    resolve_access_entries,
    sync_assistant_access,
    warn_mcp_servers_not_applied,
    warn_scope_rules_not_applied,
)


def load_space_snapshot(path: Path) -> dict[str, Any]:
    """Load a JSON or YAML space snapshot from disk."""
    return load_json_or_yaml_mapping(path)


def _emit_snapshot_warnings(
    snapshot: dict[str, Any], *, with_mcp_servers: bool = False
) -> None:
    warn_scope_rules_not_applied(list_len(snapshot.get("scopeRules")))
    if not with_mcp_servers:
        warn_mcp_servers_not_applied(list_len(snapshot.get("assistantMcpServers")))
    # With --with-mcp-servers the bindings are reported from the built payload
    # (see echo_mcp_plan), so only what is actually sent is announced.
    prompts = snapshot.get("assistantPrompts")
    if prompts:
        typer.echo(
            f"Note: snapshot lists {len(prompts)} assistant prompt(s); "
            "these will be applied on create/update.",
            err=True,
        )
    if snapshot.get("subAgentSettings") is not None:
        typer.echo(
            "Note: snapshot includes sub-agent settings; "
            "these will be applied on create/update.",
            err=True,
        )


def _validate_snapshot(snapshot: dict[str, Any], *, creating: bool) -> None:
    if snapshot.get("name") is None:
        typer.echo("Snapshot must include a non-null top-level 'name'.", err=True)
        sys.exit(2)
    if creating:
        if snapshot.get("fallbackModule") is None:
            typer.echo(
                "Snapshot must include a non-null 'fallbackModule' for create "
                "(use slot-only --destination such as `2:` or `2`).",
                err=True,
            )
            sys.exit(2)


def cmd_upsert(
    file_path: Path,
    slot: str,
    *,
    target_space_id: str | None,
    dry_run: bool,
    cwd: Path | None,
    no_access: bool = False,
    with_mcp_servers: bool = False,
) -> None:
    """Apply ``file_path`` snapshot to ``slot`` (create if ``target_space_id`` is None)."""
    try:
        snapshot = load_space_snapshot(file_path)
    except json.JSONDecodeError as exc:
        typer.echo(f"Invalid JSON in snapshot: {exc}", err=True)
        sys.exit(2)
    except yaml.YAMLError as exc:
        typer.echo(f"Invalid YAML in snapshot: {exc}", err=True)
        sys.exit(2)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        sys.exit(2)

    dst_space_id = target_space_id
    creating = dst_space_id is None
    _validate_snapshot(snapshot, creating=creating)
    _emit_snapshot_warnings(snapshot, with_mcp_servers=with_mcp_servers)

    typer.echo(f"Loading destination slot {slot!r} …")
    cfg = config_for_slot(slot, cwd=cwd)

    try:
        assistant_access = resolve_access_entries(
            snapshot.get("assistantAccess"), no_access=no_access
        )
    except SnapshotError as exc:
        typer.echo(f"Invalid snapshot: {exc}", err=True)
        sys.exit(2)

    if dst_space_id is None:
        try:
            create_params = build_create_params(snapshot, include_mcp=with_mcp_servers)
        except SnapshotError as exc:
            typer.echo(f"Invalid snapshot: {exc}", err=True)
            sys.exit(2)
        echo_mcp_plan(create_params, dry_run=dry_run)
        if dry_run:
            typer.echo(
                f"Dry-run: would create_space with name="
                f"{create_params['name']!r} and "
                f"{len(create_params['modules'])} module(s)."
            )
            if assistant_access:
                typer.echo(
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
            typer.echo(f"create_space failed: {exc}", err=True)
            echo_credential_debug_if_auth_failure(
                cfg, exc, label="space upsert create_space"
            )
            sys.exit(1)
        new_id = created["id"]
        typer.echo(f"Created space {new_id}")
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
        typer.echo(
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
        typer.echo(
            "Warning: no matching destination module for snapshot module(s) named: "
            + ", ".join(unmatched),
            err=True,
        )

    update_modules = build_module_updates_from_pairs(pairs)

    try:
        update_kw = build_update_kwargs(snapshot, include_mcp=with_mcp_servers)
    except SnapshotError as exc:
        typer.echo(f"Invalid snapshot: {exc}", err=True)
        sys.exit(2)
    echo_mcp_plan(update_kw, dry_run=dry_run)
    if update_modules:
        update_kw["modules"] = update_modules

    if dry_run:
        typer.echo(
            f"Dry-run: would update_space {dst_space_id!r} with fields "
            f"{sorted(update_kw.keys())!r}."
        )
        if assistant_access:
            typer.echo(
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
        typer.echo(f"update_space failed: {exc}", err=True)
        echo_credential_debug_if_auth_failure(
            cfg, exc, label="space upsert update_space"
        )
        sys.exit(1)

    typer.echo(f"Updated space {dst_space_id}")
    sync_assistant_access(
        cfg.user_id,
        cfg.company_id,
        dst_space_id,
        assistant_access,
        dry_run=dry_run,
        debug_cfg=cfg,
        credential_debug_label="space upsert add_space_access",
    )
