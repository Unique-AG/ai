"""Match exported MCP bindings to servers registered on a destination company."""

from __future__ import annotations

import json
from typing import Any, Literal

import typer
from unique_sdk import MCP
from unique_sdk.api_resources._mcp import McpServerDto

McpMatch = Literal["id", "name"]


def resolve_mcp_attachments(
    source_bindings: list[dict[str, Any]],
    destination_servers: list[McpServerDto],
    *,
    match: McpMatch,
    destination_space_id: str | None,
) -> tuple[list[dict[str, Any]] | None, list[str]]:
    """Return a ``mcpServers`` body and one warning line per dropped or widened server.

    ``None`` means the caller should omit ``mcpServers``. The public API leaves
    unlisted servers unchanged, and an empty ``tools`` list disables a server,
    so a binding that cannot be replayed is left out rather than sent as ``[]``.
    """
    attachments: list[dict[str, Any]] = []
    warnings: list[str] = []
    seen_destination_ids: set[str] = set()

    for binding in source_bindings:
        label = _binding_label(binding)
        if binding.get("isEnabled") is False:
            warnings.append(_drop(label, "source binding is disabled"))
            continue

        server, reason = _find_destination(binding, destination_servers, match)
        if server is None:
            warnings.append(_drop(label, reason or "no matching destination server"))
            continue

        destination_id = server["id"]
        if not destination_id:
            warnings.append(_drop(label, "destination server has no id"))
            continue

        restricted = _space_restriction_reason(server, destination_space_id)
        if restricted is not None:
            warnings.append(_drop(label, restricted))
            continue

        if destination_id in seen_destination_ids:
            warnings.append(
                _drop(label, "another snapshot binding already matched this server")
            )
            continue

        tools, tool_warnings, drop_reason = _tool_selection(binding, server)
        for tool_warning in tool_warnings:
            warnings.append(f"Warning: MCP server {label}: {tool_warning}")
        if drop_reason is not None:
            warnings.append(_drop(label, drop_reason))
            continue

        entry: dict[str, Any] = {"mcpServerId": destination_id}
        if tools is not None:
            entry["tools"] = tools
        attachments.append(entry)
        seen_destination_ids.add(destination_id)

    if not attachments:
        return None, warnings
    return attachments, warnings


def merge_mcp_servers(
    params: dict[str, Any],
    source: dict[str, Any],
    *,
    user_id: str,
    company_id: str,
    match: McpMatch,
    destination_space_id: str | None,
) -> dict[str, Any]:
    """Attach destination MCP servers that match the snapshot, or leave params unchanged.

    Lists servers on the destination even during a dry-run. A list failure omits
    ``mcpServers`` so existing destination bindings stay as they are.
    """
    bindings = [
        binding
        for binding in (source.get("assistantMcpServers") or [])
        if isinstance(binding, dict)
    ]
    if not bindings:
        return params

    try:
        listed = MCP.list_servers(user_id, company_id)
    except Exception as exc:
        typer.echo(
            "Warning: could not list destination MCP servers "
            f"({exc}); MCP bindings will not be attached.",
            err=True,
        )
        return params

    attachments, warnings = resolve_mcp_attachments(
        bindings,
        listed.get("mcpServers") or [],
        match=match,
        destination_space_id=destination_space_id,
    )
    for warning in warnings:
        typer.echo(warning, err=True)
    if attachments is None:
        return params
    merged = dict(params)
    merged["mcpServers"] = attachments
    return merged


def echo_mcp_dry_run(params: dict[str, Any]) -> None:
    """Print the ``mcpServers`` body a dry-run would send."""
    servers = params.get("mcpServers")
    if not servers:
        return
    typer.echo(
        "Dry-run: would send mcpServers=" + json.dumps(servers, separators=(",", ":"))
    )


def _find_destination(
    binding: dict[str, Any],
    destination_servers: list[McpServerDto],
    match: McpMatch,
) -> tuple[McpServerDto | None, str | None]:
    if match == "name":
        name = binding.get("name")
        if not isinstance(name, str) or not name:
            return None, "source binding has no name to match"
        matches = [
            server for server in destination_servers if server.get("name") == name
        ]
        if len(matches) == 0:
            return None, f"no server named {name!r} on the destination"
        if len(matches) > 1:
            return None, f"more than one destination server is named {name!r}"
        return matches[0], None

    server_id = binding.get("mcpServerId")
    if not isinstance(server_id, str) or not server_id:
        return None, "source binding has no mcpServerId"
    for server in destination_servers:
        if server.get("id") == server_id:
            return server, None
    return None, "no server with this id on the destination"


def _space_restriction_reason(
    server: McpServerDto,
    destination_space_id: str | None,
) -> str | None:
    if not server["isSpaceRestricted"]:
        return None
    if destination_space_id is None:
        return (
            "server is space-restricted and cannot be attached while creating a space"
        )
    if destination_space_id not in server["allowedSpaceIds"]:
        return (
            "server is space-restricted and is not allowed for space "
            f"{destination_space_id}"
        )
    return None


def _tool_selection(
    binding: dict[str, Any],
    server: McpServerDto,
) -> tuple[list[dict[str, Any]] | None, list[str], str | None]:
    """Return tools to send, warnings, and a drop reason.

    ``None`` tools means omit the field so every callable tool is enabled.
    """
    enabled_names = _enabled_tool_names(binding)
    if enabled_names is None:
        return (
            None,
            [
                "snapshot has no tool list; every callable tool on the "
                "destination server will be enabled"
            ],
            None,
        )
    if not enabled_names:
        return None, [], "snapshot has no enabled tools for this server"

    available = _destination_tool_names(server)
    kept: list[dict[str, Any]] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for name in enabled_names:
        if name not in available:
            warnings.append(f"snapshot tool {name!r} is not on the destination server")
            continue
        if name in seen:
            continue
        seen.add(name)
        kept.append({"name": name, "isEnabled": True})
    if not kept:
        return (
            None,
            warnings,
            ("none of the enabled snapshot tools exist on the destination server"),
        )
    return kept, warnings, None


def _enabled_tool_names(binding: dict[str, Any]) -> list[str] | None:
    """Enabled tool names, or ``None`` when the snapshot has no tool list."""
    if "tools" not in binding or binding.get("tools") is None:
        return None
    tools = binding.get("tools")
    if not isinstance(tools, list):
        return None
    names: list[str] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        name = tool.get("name")
        if not isinstance(name, str) or not name:
            continue
        if tool.get("isEnabled") is False:
            continue
        names.append(name)
    return names


def _destination_tool_names(server: McpServerDto) -> set[str]:
    return {tool["name"] for tool in server["tools"]}


def _binding_label(binding: dict[str, Any]) -> str:
    name = binding.get("name")
    server_id = binding.get("mcpServerId")
    name_text = name if isinstance(name, str) and name else "(unnamed)"
    id_text = server_id if isinstance(server_id, str) and server_id else "(no id)"
    return f"{name_text} ({id_text})"


def _drop(label: str, reason: str) -> str:
    return f"Warning: dropping MCP server {label}: {reason}"
