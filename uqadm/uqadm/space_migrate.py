"""Space configuration migration between credential slots."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click
from unique_sdk import Space
from unique_sdk.cli.config import Config

from uqadm.auth_debug import echo_credential_debug_if_auth_failure
from uqadm.endpoint import EndpointParseError, parse_endpoint, parse_source_endpoint
from uqadm.env import config_for_slot, normalize_api_base


def module_params_from_source(mod: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"name": mod["name"]}
    if mod.get("description") is not None:
        out["description"] = mod["description"]
    if mod.get("weight") is not None:
        out["weight"] = mod["weight"]
    if mod.get("isExternal") is not None:
        out["isExternal"] = mod["isExternal"]
    if mod.get("isCustomInstructionEnabled") is not None:
        out["isCustomInstructionEnabled"] = mod["isCustomInstructionEnabled"]
    if mod.get("configuration") is not None:
        out["configuration"] = mod["configuration"]
    if mod.get("toolDefinition") is not None:
        out["toolDefinition"] = mod["toolDefinition"]
    return out


def match_modules_by_name(
    source_modules: list[dict[str, Any]],
    dest_modules: list[dict[str, Any]],
) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], list[str]]:
    pool = list(dest_modules)
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    unmatched_names: list[str] = []
    for sm in source_modules:
        name = sm["name"]
        idx = next((i for i, d in enumerate(pool) if d["name"] == name), None)
        if idx is None:
            unmatched_names.append(name)
        else:
            pairs.append((sm, pool.pop(idx)))
    return pairs, unmatched_names


def build_create_params(src: dict[str, Any]) -> dict[str, Any]:
    modules = [module_params_from_source(m) for m in src.get("modules") or []]
    params: dict[str, Any] = {
        "name": src["name"],
        "fallbackModule": src["fallbackModule"],
        "modules": modules,
    }
    optional_keys = (
        "explanation",
        "alert",
        "chatUpload",
        "languageModel",
        "isExternal",
        "isPinned",
        "uiType",
        "settings",
    )
    for key in optional_keys:
        if src.get(key) is not None:
            params[key] = src[key]
    return params


def build_module_updates_from_pairs(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Build per-module update payloads from matched (source, destination) pairs.

    Each entry carries the destination ``moduleId`` plus any fields present on
    the source side: ``configuration``, ``name``, ``description``, ``weight``.
    Centralizes the payload shape used by both ``cmd_migrate`` and
    ``cmd_upsert``.
    """
    updates: list[dict[str, Any]] = []
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
        updates.append(um)
    return updates


def build_update_kwargs(src: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    simple = (
        "name",
        "title",
        "explanation",
        "alert",
        "chatUpload",
        "languageModel",
        "isPinned",
        "settings",
        "allowEndUserSpace",
        "uiType",
    )
    for key in simple:
        if src.get(key) is not None:
            kwargs[key] = src[key]
    return kwargs


def sync_assistant_access(
    user_id: str,
    company_id: str,
    space_id: str,
    assistant_access: list[dict[str, Any]],
    *,
    dry_run: bool,
    debug_cfg: Config | None = None,
    credential_debug_label: str = "space migrate add_space_access",
) -> None:
    if dry_run or not assistant_access:
        return
    access = [
        {
            "entityId": e["entityId"],
            "entityType": e["entityType"],
            "type": e["type"],
        }
        for e in assistant_access
        if e.get("entityId") and e.get("entityType") and e.get("type")
    ]
    if not access:
        return
    try:
        Space.add_space_access(user_id, company_id, space_id, access=access)
    except Exception as exc:
        click.echo(
            f"Warning: could not sync space access entries: {exc}",
            err=True,
        )
        if debug_cfg is not None:
            echo_credential_debug_if_auth_failure(
                debug_cfg, exc, label=credential_debug_label
            )


def cmd_migrate(
    source: str,
    destination: str,
    *,
    dry_run: bool,
    with_knowledge: bool,
    cwd: Path | None = None,
) -> None:
    try:
        src_slot, src_space_id = parse_source_endpoint(source)
        dst_slot, dst_space_id = parse_endpoint(destination)
    except EndpointParseError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)

    click.echo(f"Loading source slot {src_slot!r} …")
    src_cfg = config_for_slot(src_slot, cwd=cwd)
    src_company = src_cfg.company_id
    src_base = normalize_api_base(src_cfg.api_base)

    try:
        src_space = Space.get_space(
            src_cfg.user_id,
            src_cfg.company_id,
            src_space_id,
        )
    except Exception as exc:
        click.echo(f"Error fetching source space {src_space_id!r}: {exc}", err=True)
        echo_credential_debug_if_auth_failure(
            src_cfg, exc, label="space migrate source get_space"
        )
        sys.exit(1)

    click.echo(f"Loading destination slot {dst_slot!r} …")
    dst_cfg = config_for_slot(dst_slot, cwd=cwd)
    dst_company = dst_cfg.company_id
    dst_base = normalize_api_base(dst_cfg.api_base)

    cross_env = src_company != dst_company or src_base != dst_base

    if cross_env:
        click.echo(
            "Warning: source and destination use different company_id and/or "
            "UNIQUE_API_BASE — treating as cross-environment migrate. "
            "Folder/knowledge-linked scope data is not copied (IDs are not portable).",
            err=True,
        )

    scope_rules = src_space.get("scopeRules") or []
    if scope_rules:
        if cross_env:
            click.echo(
                f"Warning: skipping {len(scope_rules)} scope rule(s); "
                "not portable across environments.",
                err=True,
            )
        elif with_knowledge:
            click.echo(
                "Note: --with-knowledge does not yet migrate scope rules or folder "
                "graphs via API; only space payload fields handled here.",
                err=True,
            )
        else:
            click.echo(
                "Note: source has scope rules; extended same-environment migration "
                "(folders/knowledge) is available with tooling flags in future — "
                "currently only assistant configuration fields are migrated.",
            )

    mcp = src_space.get("assistantMcpServers") or []
    if mcp:
        click.echo(
            f"Warning: source lists {len(mcp)} MCP server binding(s); "
            "these are not migrated by this command.",
            err=True,
        )

    if with_knowledge and cross_env:
        click.echo(
            "Warning: --with-knowledge applies only when source and destination "
            "share the same company_id and UNIQUE_API_BASE; ignoring for this run.",
            err=True,
        )

    assistant_access = list(src_space.get("assistantAccess") or [])

    if dst_space_id is None:
        create_params = build_create_params(src_space)
        if dry_run:
            click.echo(
                f"Dry-run: would create_space on destination with name="
                f"{create_params['name']!r} and {len(create_params['modules'])} module(s)."
            )
            if assistant_access:
                click.echo(
                    f"Dry-run: would sync {len(assistant_access)} access entr(y/ies)."
                )
            return
        try:
            created = Space.create_space(
                dst_cfg.user_id,
                dst_cfg.company_id,
                **create_params,
            )
        except Exception as exc:
            click.echo(f"create_space failed: {exc}", err=True)
            echo_credential_debug_if_auth_failure(
                dst_cfg, exc, label="space migrate create_space"
            )
            sys.exit(1)
        new_id = created["id"]
        click.echo(f"Created space {new_id}")
        sync_assistant_access(
            dst_cfg.user_id,
            dst_cfg.company_id,
            new_id,
            assistant_access,
            dry_run=dry_run,
            debug_cfg=dst_cfg,
        )
        return

    try:
        dest_space = Space.get_space(
            dst_cfg.user_id,
            dst_cfg.company_id,
            dst_space_id,
        )
    except Exception as exc:
        click.echo(
            f"Error fetching destination space {dst_space_id!r}: {exc}",
            err=True,
        )
        echo_credential_debug_if_auth_failure(
            dst_cfg, exc, label="space migrate destination get_space"
        )
        sys.exit(1)
    pairs, unmatched = match_modules_by_name(
        list(src_space.get("modules") or []),
        list(dest_space.get("modules") or []),
    )
    if unmatched:
        click.echo(
            "Warning: no matching destination module for source module(s) named: "
            + ", ".join(unmatched),
            err=True,
        )

    update_modules = build_module_updates_from_pairs(pairs)

    update_kw = build_update_kwargs(src_space)
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
            dst_cfg.user_id,
            dst_cfg.company_id,
            dst_space_id,
            **update_kw,
        )
    except Exception as exc:
        click.echo(f"update_space failed: {exc}", err=True)
        echo_credential_debug_if_auth_failure(
            dst_cfg, exc, label="space migrate update_space"
        )
        sys.exit(1)

    click.echo(f"Updated space {dst_space_id}")
    sync_assistant_access(
        dst_cfg.user_id,
        dst_cfg.company_id,
        dst_space_id,
        assistant_access,
        dry_run=dry_run,
        debug_cfg=dst_cfg,
    )
