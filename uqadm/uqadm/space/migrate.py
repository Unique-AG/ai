"""Space configuration migration between credential slots."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, cast

import typer
from unique_sdk import Space
from unique_sdk.cli.config import Config

from uqadm.core.auth_debug import echo_credential_debug_if_auth_failure
from uqadm.core.endpoint import (
    EndpointParseError,
    parse_endpoint,
    parse_source_endpoint,
)
from uqadm.core.env import config_for_slot, normalize_api_base


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


def plain_json_value(value: Any) -> Any:
    """Copy mappings/lists to plain JSON-friendly containers (UniqueObject → dict)."""
    if isinstance(value, dict):
        return {k: plain_json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [plain_json_value(item) for item in value]
    return value


def _as_switchable_model_entries(models: Any) -> list[Any]:
    if models is None:
        return []
    if isinstance(models, list):
        return list(models)
    if isinstance(models, dict):
        data = models.get("data")
        if isinstance(data, list):
            return list(data)
        if "displayName" in models and "languageModel" in models:
            return [models]
    return []


def switchable_language_model_params_from_source(
    models: Any,
) -> list[dict[str, Any]]:
    """Keep allowed model-picker fields; drop extra snapshot keys unique-api rejects."""
    out: list[dict[str, Any]] = []
    for model in _as_switchable_model_entries(models):
        if not isinstance(model, dict):
            continue
        display_name = model.get("displayName")
        language_model = model.get("languageModel")
        if display_name is None or language_model is None:
            continue
        item: dict[str, Any] = {
            "displayName": display_name,
            "languageModel": plain_json_value(language_model),
        }
        if model.get("temperature") is not None:
            item["temperature"] = model["temperature"]
        if model.get("additionalLLMOptions") is not None:
            item["additionalLLMOptions"] = plain_json_value(
                model["additionalLLMOptions"]
            )
        out.append(item)
    return out


def assistant_prompt_params_from_source(
    prompts: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Map export snapshot prompts to Space API assistantPrompts payloads.

    Source ``id`` values are intentionally dropped: they identify prompts of the
    *source* space and are meaningless (and unsafe to forward) when creating a
    new space or migrating/upserting into a different one. Omitting them makes
    the operation a clean full replacement on the server (delete-all +
    create-all), mirroring how module creates omit source module ids.
    """
    if not prompts:
        return []
    out: list[dict[str, Any]] = []
    for prompt in prompts:
        item: dict[str, Any] = {
            "title": prompt["title"],
            "prompt": prompt["prompt"],
        }
        if prompt.get("order") is not None:
            item["order"] = prompt["order"]
        out.append(item)
    return out


class SnapshotError(ValueError):
    """A space snapshot/source payload field has a shape uqadm cannot apply."""


def _mcp_tool_params(server_id: str, tools: Any) -> list[dict[str, Any]] | None:
    """Validate an explicit tool selection; ``None`` means "enable all tools"."""
    if tools is None:
        return None
    if not isinstance(tools, list):
        raise SnapshotError(
            f"MCP binding {server_id!r}: 'tools' must be a list, "
            f"got {type(tools).__name__}."
        )
    out: list[dict[str, Any]] = []
    for idx, tool in enumerate(tools):
        name = tool.get("name") if isinstance(tool, dict) else None
        if not isinstance(name, str) or not name:
            raise SnapshotError(
                f"MCP binding {server_id!r}: tools[{idx}] must be a mapping "
                "with a non-empty string 'name'."
            )
        enabled = tool.get("isEnabled")
        if not isinstance(enabled, bool):
            # Never coerce: bool("false") is True and would enable the tool.
            raise SnapshotError(
                f"MCP binding {server_id!r}: tools[{idx}] ({name!r}) "
                f"'isEnabled' must be true or false, got {enabled!r}."
            )
        out.append({"name": name, "isEnabled": enabled})
    # An empty selection on an enabled binding carries no explicit choice, so
    # keep the "enable every callable tool" form rather than disabling it.
    return out or None


def mcp_server_params_from_source(entries: Any) -> list[dict[str, Any]]:
    """Map exported ``assistantMcpServers`` to Space API ``mcpServers`` payloads.

    Drops source-only keys (binding ``id``, ``assistantId``, timestamps). A
    disabled binding maps to ``tools: []``, which disables the server for the
    space. An enabled binding with no (or an empty) tool list omits ``tools``
    so every callable tool is enabled.

    Raises:
        SnapshotError: If the bindings, or an explicit tool selection, are
            malformed. Invalid selections are rejected rather than silently
            widened to "enable all tools".
    """
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise SnapshotError(
            f"'assistantMcpServers' must be a list, got {type(entries).__name__}."
        )
    out: list[dict[str, Any]] = []
    for idx, entry in enumerate(entries):
        server_id = entry.get("mcpServerId") if isinstance(entry, dict) else None
        if (
            not isinstance(entry, dict)
            or not isinstance(server_id, str)
            or not server_id
        ):
            raise SnapshotError(
                f"assistantMcpServers[{idx}] must be a mapping with a non-empty "
                "string 'mcpServerId'."
            )
        binding_enabled = entry.get("isEnabled", True)
        if not isinstance(binding_enabled, bool):
            # A non-boolean state must not fall through to "enable all tools".
            raise SnapshotError(
                f"MCP binding {server_id!r}: 'isEnabled' must be true or false, "
                f"got {binding_enabled!r}."
            )
        item: dict[str, Any] = {"mcpServerId": server_id}
        if binding_enabled is False:
            item["tools"] = []
        else:
            tools = _mcp_tool_params(server_id, entry.get("tools"))
            if tools is not None:
                item["tools"] = tools
        out.append(item)
    return out


def warn_scope_rules_not_applied(count: int, *, reason: str | None = None) -> None:
    """Emit the single, consistent warning that scope rules are not copied."""
    if count <= 0:
        return
    detail = reason or "no public API to write scope rules"
    typer.echo(
        f"Warning: {count} scope rule(s) are NOT applied ({detail}); "
        "configure them manually in the destination space.",
        err=True,
    )


def warn_mcp_servers_not_applied(count: int) -> None:
    """Point users at ``--with-mcp-servers`` when bindings are being skipped."""
    if count <= 0:
        return
    typer.echo(
        f"Warning: {count} MCP server binding(s) are not applied; "
        "pass --with-mcp-servers to include them.",
        err=True,
    )


def list_len(value: Any) -> int:
    """Length of ``value`` if it is a list, else 0 (for warning counts only)."""
    return len(value) if isinstance(value, list) else 0


def echo_mcp_plan(params: dict[str, Any], *, dry_run: bool) -> None:
    """Report the MCP bindings actually present in a built create/update payload."""
    mcp = params.get("mcpServers") or []
    if not mcp:
        return
    verb = "Dry-run: would apply" if dry_run else "Applying"
    typer.echo(
        f"{verb} {len(mcp)} MCP server binding(s); mcpServerId values must "
        "exist in the destination environment.",
        err=True,
    )


ACCESS_KEYS: tuple[str, ...] = ("assistantAccess", "access")


def strip_access_keys(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of a space payload without top-level access keys."""
    return {k: v for k, v in payload.items() if k not in ACCESS_KEYS}


def resolve_access_entries(raw: Any, *, no_access: bool) -> list[dict[str, Any]]:
    """Return the access entries to merge, or none when ``no_access`` is set.

    ``raw`` is the unparsed ``assistantAccess`` field; with ``no_access`` it is
    never parsed, so a malformed field cannot block an ACL-preserving run.

    Raises:
        SnapshotError: If ``no_access`` is unset and ``raw`` is not a list.
    """
    if no_access:
        count = len(raw) if isinstance(raw, list) else 0
        typer.echo(
            f"Note: --no-access set; skipping {count} access entr(y/ies). "
            "Destination ACL is left untouched.",
            err=True,
        )
        return []
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise SnapshotError(
            f"'assistantAccess' must be a list, got {type(raw).__name__}."
        )
    return list(raw)


def build_create_params(
    src: dict[str, Any], *, include_mcp: bool = False
) -> dict[str, Any]:
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
        "isSubAgent",
        "subAgentSettings",
    )
    for key in optional_keys:
        if src.get(key) is not None:
            params[key] = src[key]
    # Model-switching settings must travel together: enabling the toggle
    # without the accompanying model list would create a space with a null
    # allowlist. Whenever the toggle is set, forward the list too
    # (defaulting to an empty list), mirroring build_update_kwargs.
    if src.get("allowModelSwitching") is not None:
        params["allowModelSwitching"] = src["allowModelSwitching"]
        params["switchableLanguageModels"] = (
            switchable_language_model_params_from_source(
                src.get("switchableLanguageModels")
            )
        )
    elif "switchableLanguageModels" in src:
        params["switchableLanguageModels"] = (
            switchable_language_model_params_from_source(
                src["switchableLanguageModels"]
            )
        )
    if src.get("assistantPrompts"):
        params["assistantPrompts"] = assistant_prompt_params_from_source(
            src["assistantPrompts"]
        )
    if include_mcp:
        mcp = mcp_server_params_from_source(src.get("assistantMcpServers"))
        if mcp:
            params["mcpServers"] = mcp
    return params


def build_module_updates_from_pairs(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Build per-module update payloads from matched (source, destination) pairs."""
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


def build_update_kwargs(
    src: dict[str, Any], *, include_mcp: bool = False
) -> dict[str, Any]:
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
        "isSubAgent",
        "subAgentSettings",
    )
    for key in simple:
        if src.get(key) is not None:
            kwargs[key] = src[key]
    # Model-switching settings must travel together: forwarding the toggle
    # without the accompanying model list would leave a stale/partial
    # switchable-model list on the destination. Whenever the toggle is
    # migrated, sync the list too (defaulting to an empty list).
    if src.get("allowModelSwitching") is not None:
        kwargs["allowModelSwitching"] = src["allowModelSwitching"]
        kwargs["switchableLanguageModels"] = (
            switchable_language_model_params_from_source(
                src.get("switchableLanguageModels")
            )
        )
    elif "switchableLanguageModels" in src:
        kwargs["switchableLanguageModels"] = (
            switchable_language_model_params_from_source(
                src["switchableLanguageModels"]
            )
        )
    if "assistantPrompts" in src:
        kwargs["assistantPrompts"] = assistant_prompt_params_from_source(
            src["assistantPrompts"]
        )
    if include_mcp:
        mcp = mcp_server_params_from_source(src.get("assistantMcpServers"))
        if mcp:
            kwargs["mcpServers"] = mcp
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
    access = cast(
        "list[Space.AccessEntry]",
        [
            {
                "entityId": e["entityId"],
                "entityType": e["entityType"],
                "type": e["type"],
            }
            for e in assistant_access
            if e.get("entityId") and e.get("entityType") and e.get("type")
        ],
    )
    if not access:
        return
    try:
        Space.add_space_access(user_id, company_id, space_id, access=access)
    except Exception as exc:
        typer.echo(
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
    no_access: bool = False,
    with_mcp_servers: bool = False,
) -> None:
    try:
        src_slot, src_space_id = parse_source_endpoint(source)
        dst_slot, dst_space_id = parse_endpoint(destination)
    except EndpointParseError as exc:
        typer.echo(str(exc), err=True)
        sys.exit(2)

    typer.echo(f"Loading source slot {src_slot!r} …")
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
        typer.echo(f"Error fetching source space {src_space_id!r}: {exc}", err=True)
        echo_credential_debug_if_auth_failure(
            src_cfg, exc, label="space migrate source get_space"
        )
        sys.exit(1)

    typer.echo(f"Loading destination slot {dst_slot!r} …")
    dst_cfg = config_for_slot(dst_slot, cwd=cwd)
    dst_company = dst_cfg.company_id
    dst_base = normalize_api_base(dst_cfg.api_base)

    cross_env = src_company != dst_company or src_base != dst_base

    if cross_env:
        typer.echo(
            "Warning: source and destination use different company_id and/or "
            "UNIQUE_API_BASE — treating as cross-environment migrate. "
            "Folder/knowledge-linked scope data is not copied (IDs are not portable).",
            err=True,
        )

    warn_scope_rules_not_applied(list_len(src_space.get("scopeRules")))

    mcp_count = list_len(src_space.get("assistantMcpServers"))
    include_mcp = with_mcp_servers
    if with_mcp_servers and cross_env:
        include_mcp = False
        if mcp_count:
            typer.echo(
                f"Warning: --with-mcp-servers ignored for cross-environment migrate; "
                f"skipping {mcp_count} MCP server binding(s) (ids are not portable).",
                err=True,
            )
    elif not with_mcp_servers:
        warn_mcp_servers_not_applied(mcp_count)

    if with_knowledge and cross_env:
        typer.echo(
            "Warning: --with-knowledge applies only when source and destination "
            "share the same company_id and UNIQUE_API_BASE; ignoring for this run.",
            err=True,
        )

    try:
        assistant_access = resolve_access_entries(
            src_space.get("assistantAccess"), no_access=no_access
        )
    except SnapshotError as exc:
        typer.echo(f"Invalid source space: {exc}", err=True)
        sys.exit(2)

    if dst_space_id is None:
        try:
            create_params = build_create_params(src_space, include_mcp=include_mcp)
        except SnapshotError as exc:
            typer.echo(f"Invalid source space: {exc}", err=True)
            sys.exit(2)
        echo_mcp_plan(create_params, dry_run=dry_run)
        if dry_run:
            typer.echo(
                f"Dry-run: would create_space on destination with name="
                f"{create_params['name']!r} and {len(create_params['modules'])} module(s)."
            )
            if assistant_access:
                typer.echo(
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
            typer.echo(f"create_space failed: {exc}", err=True)
            echo_credential_debug_if_auth_failure(
                dst_cfg, exc, label="space migrate create_space"
            )
            sys.exit(1)
        new_id = created["id"]
        typer.echo(f"Created space {new_id}")
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
        typer.echo(
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
        typer.echo(
            "Warning: no matching destination module for source module(s) named: "
            + ", ".join(unmatched),
            err=True,
        )

    update_modules = build_module_updates_from_pairs(pairs)

    try:
        update_kw = build_update_kwargs(src_space, include_mcp=include_mcp)
    except SnapshotError as exc:
        typer.echo(f"Invalid source space: {exc}", err=True)
        sys.exit(2)
    if update_modules:
        update_kw["modules"] = update_modules
    echo_mcp_plan(update_kw, dry_run=dry_run)

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
            dst_cfg.user_id,
            dst_cfg.company_id,
            dst_space_id,
            **update_kw,
        )
    except Exception as exc:
        typer.echo(f"update_space failed: {exc}", err=True)
        echo_credential_debug_if_auth_failure(
            dst_cfg, exc, label="space migrate update_space"
        )
        sys.exit(1)

    typer.echo(f"Updated space {dst_space_id}")
    sync_assistant_access(
        dst_cfg.user_id,
        dst_cfg.company_id,
        dst_space_id,
        assistant_access,
        dry_run=dry_run,
        debug_cfg=dst_cfg,
    )
