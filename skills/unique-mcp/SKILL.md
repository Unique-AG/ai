---
name: unique-mcp
description: >-
  Applies Unique FastMCP server best practices: unique-mcp identity injectors,
  unique.app/_meta config and context requirements, Zitadel OAuth, Unique AI
  tool listing, and per-request UniqueSettings. Use when building, reviewing,
  or extending MCP servers, FastMCP tools, Unique AI connectors, unique_mcp,
  or tools/list and tools/call _meta.
license: MIT
compatibility: claude cursor opencode
metadata:
  version: "1.0.0"
  languages: python
  audience: developers
  workflow: mcp
  since: "2026-08-21"
---

# Unique MCP best practices

Default stack: **FastMCP ≥ 3.3**, **Python ≥ 3.12**, **`unique-mcp`**, HTTP/streamable transport. Do not invent a second auth or config channel.

## When to use

Building, reviewing, or extending an MCP server that Unique AI (or another Unique host) will call. Especially: new `@tool`s, `_meta`, Zitadel/OAuth, `UniqueSettings`, or connector admin config.

## Workflow

1. Read this file fully.
2. For `_meta` keys, advertise/inject split, and injectors → [meta.md](meta.md).
3. For identity ranking, token swap, and `_meta` auth security → [identity.md](identity.md).
4. When writing or reviewing a tool, match [examples.md](examples.md).
5. Apply the hard rules below. Fail the review if any are violated.

## Hard rules

1. **LLM-visible state vs admin config.** Tool *arguments* are what the model fills (query, `content_id`, mode). Admin-chosen behaviour (limits, filters, rerankers) is a Pydantic config model advertised with `ConfigSchemaMeta` and injected with `Depends(get_tool_config(Model))`. Never put admin knobs in the tool input schema.
2. **Advertise on `tools/list`, inject on `tools/call`.** Use `merge_tool_meta(...)` as `@tool(..., meta=_META)`. Unique AI reads `unique.app/config-schema` and `unique.app/context-requirements` at list time, then sends `unique.app/config` plus requested context keys at call time.
3. **Namespace every custom `_meta` key `unique.app/…`.** Do not use flat camelCase (`userId`) in new code. Do not use `mcp/` or `modelcontextprotocol/` prefixes (protocol-reserved).
4. **Config models must have defaults on every field.** `ConfigSchemaMeta` raises `TypeError` otherwise — the admin UI needs a complete starting config.
5. **Identity: `await get_unique_settings_async()` in the tool body**, not as `Depends`. A refused-identity `ValueError` must surface as a tool error (`CallToolResult(isError=True)`), not a FastMCP dependency failure. Prefer async over deprecated `get_unique_settings()`.
6. **Never honour `_meta` auth when a bearer token is present.** `unique-mcp` already ignores `unique.app/auth/*` once `Authorization` is set. Do not reimplement identity lookup that trusts `_meta` over the JWT.
7. **Do not set `UNIQUE_AUTH_USER_ID` / `UNIQUE_AUTH_COMPANY_ID` in production.** Those are local unauthenticated fallbacks. Incomplete tokens must raise, not silently run as a service user.
8. **OAuth `client_storage` is required.** Pass a shared store in prod (e.g. Postgres + encryption). `MemoryStore()` is local-dev only. Never omit the argument.
9. **Wire Zitadel through `unique-mcp` proxies** (`create_zitadel_oidc_proxy` or `create_zitadel_oauth_proxy`). Do not hand-roll JWT parsing or talk to Zitadel `/userinfo` from tools.
10. **Return MCP tool errors, don't throw past the handler.** Catch, log, return `CallToolResult(isError=True, content=[TextContent(...)])`.
11. **Ops:** `configure_logging()`, `setup_ops(mcp)` for `/health` `/probe` `/metrics`. Explicit `client_storage`. HTTPS + public `UNIQUE_MCP_PUBLIC_BASE_URL` for OAuth callbacks.
12. **Unique AI listing:** set `unique.app/icon`, `unique.app/system-prompt`, and `unique.app/tool-format-information` (via `UniqueAIToolMeta` or the `merge_tool_meta` base dict). Set honest `ToolAnnotations` (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`).

## Checklist (every new tool)

- [ ] `@tool(..., meta=_META)` with `merge_tool_meta`
- [ ] `ContextRequirements` lists required `MetaKeys` (at least `USER_ID` + `COMPANY_ID` if Unique APIs are called)
- [ ] `ConfigSchemaMeta(ConfigModel)` if the tool has admin settings; all fields have defaults
- [ ] `Depends(get_tool_config(ConfigModel))` for that model
- [ ] `settings = await get_unique_settings_async()` inside `try` / tool-error `except`
- [ ] No secrets, tokens, or tenant IDs in tool arguments
- [ ] No `get_context().request_context.meta` — use `get_request_meta()` for custom keys

## Do not

- Put `user_id` / `company_id` in the tool JSON schema
- Trust caller-supplied identity on authenticated requests
- Use FastMCP's default on-disk OAuth store in Kubernetes
- Fall back to env identity when an access token is present
- Duplicate Unique API clients instead of `UniqueSettings` / toolkit services

## Install (skills.sh)

```bash
npx skills add Unique-AG/ai/skills/unique-mcp
# or
npx skills add Unique-AG/ai --skill unique-mcp
```

Canonical package docs (this repo): [`unique_mcp/docs`](https://github.com/Unique-AG/ai/tree/main/unique_mcp/docs). In-repo example: [`tutorials/mcp/mcp_search`](https://github.com/Unique-AG/ai/tree/main/tutorials/mcp/mcp_search).
