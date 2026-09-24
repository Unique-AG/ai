# unique_mcp documentation

Guides that sit alongside the package [README](../README.md). The README is the quick start (construct a FastMCP server, public exports). These pages hold the rest.

| Page | What it covers |
| ---- | -------------- |
| [Per-request identity](identity.md) | Token swap, resolution order, OAuth scopes, and the three auth scenarios |
| [MCP `_meta` convention](meta.md) | How Unique uses the MCP `_meta` field for config, context requirements, identity, and chat — including the FastMCP injectors that read it back |
| [Configuration](configuration.md) | Env vars, env files, logging and metrics |
| [Zitadel setup](zitadel.md) | Creating the OAuth app, JWT token type, redirect URIs, and wiring the proxy |
| [Agent skill](../../skills/unique-mcp/) | `npx skills add Unique-AG/ai/skills/unique-mcp` — Unique MCP best practices for coding agents |
