# unique_mcp

Shared library for Unique FastMCP servers: auth, request context, and per-tool admin configuration.

## Language

**Tool config**:
Admin-set settings for one MCP tool, expressed as a pydantic model such as `SearchToolConfig`.
_Avoid_: tool arguments, MCP function name

**Tool config key**:
The env-var segment taken from a tool config's class name (`SearchToolConfig` → `SEARCH_TOOL`).
_Avoid_: MCP function name, server display name
