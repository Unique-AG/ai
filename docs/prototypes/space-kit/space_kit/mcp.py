"""MCP server selection for a space.

A space stores MCP in two places: the attachment tables (what
`assistantMcpServers` returns and what the runtime advertises) and MCP tool
entries in the module `configuration.tools`. The public `mcpServers` field
writes the tables and wins over the module entries, so both are kept equal.
"""

import copy

from pydantic import Field

from space_kit.base import (
    JsonObject,
    JsonValue,
    KitModel,
    SpaceKitError,
    as_list,
    text_or_empty,
)

ALL_TOOLS = "all"
NO_TOOLS = "none"

type Selection = dict[str, frozenset[str]]


class McpServerInfo(KitModel):
    id: str
    name: str
    callable_tools: frozenset[str]
    is_space_restricted: bool = False
    allowed_space_ids: frozenset[str] = frozenset()


class McpCatalog(KitModel):
    servers: tuple[McpServerInfo, ...]

    @classmethod
    def from_api(cls, *, rows: list[JsonObject]) -> "McpCatalog":
        return cls(servers=tuple(_server_info(row=row) for row in rows))

    def by_id(self, *, server_id: str) -> McpServerInfo | None:
        return next((s for s in self.servers if s.id == server_id), None)

    def named(self, *, name: str) -> list[McpServerInfo]:
        return [s for s in self.servers if s.name == name]

    def resolve(self, *, ref: str) -> McpServerInfo:
        found = self.by_id(server_id=ref)
        if found is not None:
            return found
        matches = self.named(name=ref)
        if len(matches) == 1:
            return matches[0]
        if not matches:
            msg = f"no MCP server with id or name {ref!r}; see `mcp list`"
            raise SpaceKitError(msg)
        ids = ", ".join(s.id for s in matches)
        msg = f"MCP server name {ref!r} is ambiguous ({ids}); use the id"
        raise SpaceKitError(msg)


def _server_info(*, row: JsonObject) -> McpServerInfo:
    tools = as_list(value=row.get("tools"), what="MCP server tools")
    allowed = as_list(value=row.get("allowedSpaceIds"), what="allowedSpaceIds")
    return McpServerInfo(
        id=text_or_empty(value=row.get("id")),
        name=text_or_empty(value=row.get("name")),
        callable_tools=frozenset(
            text_or_empty(value=tool.get("name"))
            for tool in tools
            if isinstance(tool, dict)
        ),
        is_space_restricted=row.get("isSpaceRestricted") is True,
        allowed_space_ids=frozenset(item for item in allowed if isinstance(item, str)),
    )


class McpChange(KitModel):
    server: str
    tools: str | tuple[str, ...]


class McpPlan(KitModel):
    replace: bool = False
    changes: tuple[McpChange, ...] = ()
    id_map: dict[str, str] = Field(default_factory=dict)
    skip_restricted: bool = False
    drop_unmapped: bool = False


class SelectionResult(KitModel):
    selection: Selection
    warnings: tuple[str, ...] = ()
    dropped_servers: frozenset[str] = frozenset()


def parse_change(*, text: str) -> McpChange:
    server, separator, tools = text.rpartition("=")
    if not separator or not server.strip() or not tools.strip():
        msg = f"expected server=all|none|tool1,tool2, got {text!r}"
        raise SpaceKitError(msg)
    value = tools.strip()
    if value in {ALL_TOOLS, NO_TOOLS}:
        return McpChange(server=server.strip(), tools=value)
    names = tuple(name.strip() for name in value.split(",") if name.strip())
    return McpChange(server=server.strip(), tools=names)


def _attachment_enabled(*, attachment: JsonObject) -> frozenset[str]:
    if attachment.get("isEnabled") is not True:
        return frozenset()
    tools = as_list(value=attachment.get("tools"), what="attachment tools")
    return frozenset(
        text_or_empty(value=tool.get("name"))
        for tool in tools
        if isinstance(tool, dict) and tool.get("isEnabled") is True
    )


def config_server_ids(*, configuration: JsonObject) -> set[str]:
    ids: set[str] = set()
    for entry in as_list(value=configuration.get("tools"), what="tools"):
        server = _mcp_entry_server(entry=entry)
        if server:
            ids.add(server)
    return ids


def attachment_server_ids(*, space: JsonObject) -> set[str]:
    attachments = as_list(
        value=space.get("assistantMcpServers"), what="assistantMcpServers"
    )
    return {
        text_or_empty(value=a.get("mcpServerId"))
        for a in attachments
        if isinstance(a, dict)
    }


def build_id_map(
    *,
    source_ids: set[str],
    source: McpCatalog,
    target: McpCatalog,
    explicit: dict[str, str],
) -> tuple[dict[str, str], tuple[str, ...]]:
    """Maps source server ids to target ids by unique name. Returns the
    map and a description of every server that has no unique match."""
    id_map = dict(explicit)
    unmapped: list[str] = []
    for server_id in sorted(source_ids - set(explicit)):
        info = source.by_id(server_id=server_id)
        name = info.name if info else ""
        matches = target.named(name=name) if name else []
        if len(matches) == 1:
            id_map[server_id] = matches[0].id
        else:
            unmapped.append(
                f"{server_id} ({name or 'unknown name'}): "
                f"{len(matches)} servers with that name on the target"
            )
    return id_map, tuple(unmapped)


def template_selection(
    *,
    space: JsonObject,
    catalog: McpCatalog,
    id_map: dict[str, str],
) -> SelectionResult:
    selection: Selection = {}
    warnings: list[str] = []
    dropped: set[str] = set()
    attachments = as_list(
        value=space.get("assistantMcpServers"), what="assistantMcpServers"
    )
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        source_id = text_or_empty(value=attachment.get("mcpServerId"))
        server_id = id_map.get(source_id, source_id)
        info = catalog.by_id(server_id=server_id)
        if info is None:
            dropped.add(server_id)
            warnings.append(
                f"MCP server {server_id} is attached to the template but not "
                "usable on the target; it is left out"
            )
            continue
        enabled = _attachment_enabled(attachment=attachment)
        stale = enabled - info.callable_tools
        if stale:
            warnings.append(
                f"{info.name}: the server no longer exposes "
                f"{', '.join(sorted(stale))}; they are left out of the "
                "attachment (the API rejects them), module config unchanged"
            )
        selection[server_id] = enabled & info.callable_tools
    return SelectionResult(
        selection=selection,
        warnings=tuple(warnings),
        dropped_servers=frozenset(dropped),
    )


def apply_changes(
    *,
    selection: Selection,
    changes: tuple[McpChange, ...],
    catalog: McpCatalog,
) -> Selection:
    result = dict(selection)
    for change in changes:
        info = catalog.resolve(ref=change.server)
        if change.tools == ALL_TOOLS:
            result[info.id] = info.callable_tools
            continue
        if change.tools == NO_TOOLS:
            result[info.id] = frozenset()
            continue
        requested = frozenset(change.tools)
        unknown = requested - info.callable_tools
        if unknown:
            msg = (
                f"{info.name} has no callable tool(s) "
                f"{', '.join(sorted(unknown))}; callable: "
                f"{', '.join(sorted(info.callable_tools))}"
            )
            raise SpaceKitError(msg)
        result[info.id] = requested
    return result


def check_restricted(
    *,
    selection: Selection,
    catalog: McpCatalog,
    space_id: str | None,
    skip: bool,
) -> SelectionResult:
    kept: Selection = {}
    warnings: list[str] = []
    dropped: set[str] = set()
    for server_id, tools in selection.items():
        info = catalog.by_id(server_id=server_id)
        allowed = info is None or not info.is_space_restricted
        if info is not None and space_id in info.allowed_space_ids:
            allowed = True
        if allowed:
            kept[server_id] = tools
            continue
        name = info.name if info else server_id
        if not skip:
            msg = (
                f"MCP server {name} ({server_id}) is space-restricted and "
                "this space is not on its allow-list. The public API cannot "
                "allow-list a space: create without it (--skip-restricted), "
                "add the space to the server in the admin UI, then run "
                "`edit` with --mcp."
            )
            raise SpaceKitError(msg)
        dropped.add(server_id)
        warnings.append(f"space-restricted MCP server {name} left out")
    return SelectionResult(
        selection=kept,
        warnings=tuple(warnings),
        dropped_servers=frozenset(dropped),
    )


def to_request(*, selection: Selection) -> list[JsonValue]:
    request: list[JsonValue] = []
    for server_id in sorted(selection):
        tools: list[JsonValue] = [
            {"name": name, "isEnabled": True} for name in sorted(selection[server_id])
        ]
        request.append({"mcpServerId": server_id, "tools": tools})
    return request


def _mcp_entry_server(*, entry: JsonValue) -> str:
    if not isinstance(entry, dict):
        return ""
    inner = entry.get("configuration")
    if not isinstance(inner, dict) or inner.get("mcpTool") is not True:
        return ""
    return text_or_empty(value=inner.get("mcpServerId"))


def sync_config_tools(
    *,
    configuration: JsonObject,
    selection: Selection,
    catalog: McpCatalog,
    id_map: dict[str, str],
    drop_servers: frozenset[str],
    disable_unselected: bool = False,
) -> JsonObject:
    """Remaps MCP entries in `configuration.tools` and sets `isEnabled`
    from the selection, so the module and the attachment tables agree.

    With `disable_unselected` (`--mcp-replace`), entries of servers that
    are not in the selection are switched off as well.

    Entries for tools the server no longer exposes keep their state:
    nothing can call them, and harness-eval fingerprints the union of
    both MCP sources, so flipping them would differ from the template."""
    result = copy.deepcopy(configuration)
    entries = as_list(value=result.get("tools"), what="tools")
    kept: list[JsonValue] = []
    for entry in entries:
        source_id = _mcp_entry_server(entry=entry)
        if not source_id or not isinstance(entry, dict):
            kept.append(entry)
            continue
        server_id = id_map.get(source_id, source_id)
        if server_id in drop_servers or source_id in drop_servers:
            continue
        inner = entry["configuration"]
        assert isinstance(inner, dict)
        inner["mcpServerId"] = server_id
        name = text_or_empty(value=entry.get("name"))
        info = catalog.by_id(server_id=server_id)
        if disable_unselected and server_id not in selection:
            entry["isEnabled"] = False
        elif (
            server_id in selection and info is not None and name in info.callable_tools
        ):
            entry["isEnabled"] = name in selection[server_id]
        kept.append(entry)
    if "tools" in result:
        result["tools"] = kept
    return result


def describe_selection(*, selection: Selection, catalog: McpCatalog) -> list[str]:
    lines: list[str] = []
    for server_id in sorted(selection):
        info = catalog.by_id(server_id=server_id)
        name = info.name if info else server_id
        tools = selection[server_id]
        total = len(info.callable_tools) if info else len(tools)
        state = "disabled" if not tools else f"{len(tools)}/{total} tools"
        lines.append(f"{name} ({server_id}): {state}")
    return lines
