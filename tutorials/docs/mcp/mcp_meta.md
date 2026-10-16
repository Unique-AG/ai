# Unique MCP `_meta`

## 📌 Overview

The [Model Context Protocol](https://modelcontextprotocol.io/) reserves an optional `_meta` object on JSON-RPC requests, tool definitions, and content items. Unique MCP servers use that field — namespaced under `unique.app/` — as a side channel for data the LLM should not invent: admin-chosen tool config, the current chat, and tenant identity.

This page is the Unique-AI-oriented overview. The package reference (key catalogue, injectors, security ranking) lives in [`unique_mcp/docs/meta.md`](../../../unique_mcp/docs/meta.md).

**Prerequisites:** [MCP Fundamentals](mcp_fundamentals.md) and a FastMCP server that depends on `unique-mcp`.

## 🎯 Two directions, one field

MCP `_meta` is opaque extra data. Implementations must ignore unknown keys, and custom keys should use reverse-DNS prefixes. Unique therefore publishes every key as `unique.app/…`.

The same field is written by **different sides** at different times:

| Surface | Who writes | What Unique puts there |
| ------- | ---------- | ---------------------- |
| `tools/list` | MCP **server** | Config schema, context requirements, icon, Unique AI prompt fragments |
| `tools/call` | MCP **host** (Unique AI, Inspector, internal services) | Saved admin config, auth ids, chat ids |

```mermaid
flowchart LR
    subgraph list ["tools/list — server advertises"]
        Schema["unique.app/config-schema"]
        Reqs["unique.app/context-requirements"]
        UI["icon / system-prompt"]
    end
    subgraph call ["tools/call — host injects"]
        Config["unique.app/config"]
        Auth["unique.app/auth/*"]
        Chat["unique.app/chat/*"]
    end
    list -->|"Unique AI admin UI + runtime"| call
    call --> DI["unique_mcp injectors"]
```

Tool **arguments** stay in `params.arguments` (the search string, the `content_id`). Config and context stay in `_meta` so they never appear in the LLM-facing schema.

## 📣 Advertising on `tools/list`

Build a meta dict with `merge_tool_meta`, then pass it to FastMCP's `@tool(..., meta=_META)`.

```python
from unique_mcp import (
    ConfigSchemaMeta,
    ContextRequirements,
    MetaKeys,
    UniqueAIToolMeta,
    merge_tool_meta,
)

_META = merge_tool_meta(
    {"unique.app/icon": "search"},
    ContextRequirements(required=[MetaKeys.USER_ID, MetaKeys.COMPANY_ID]),
    ConfigSchemaMeta(SearchToolConfig),
    UniqueAIToolMeta(
        tool_description_for_system_prompt="Choose this tool to search the knowledge base.",
        tool_format_information_for_system_prompt="Cite results with the markdown links the tool returns.",
    ),
)
```

- **`ConfigSchemaMeta`** — JSON Schema + RJSF `ui_schema` + `default_config` at `unique.app/config-schema`. Unique AI renders this as the connector/tool admin form. Every Pydantic field needs a default.
- **`ContextRequirements`** — which `_meta` keys Unique AI should copy from the current chat/user onto `tools/call`.
- **`UniqueAIToolMeta` / icon** — presentation only; Unique AI uses them in the space UI and system prompt. They are not echoed back on the call.

The in-repo example is [`mcp_search`](https://github.com/Unique-AG/ai/tree/main/tutorials/mcp/mcp_search).

## 📥 Injecting on `tools/call`

Unique AI (or any trusted host) then sends:

```json
{
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": { "search_string": "Q3 revenue" },
    "_meta": {
      "unique.app/config": { "limit": 10 },
      "unique.app/auth/user-id": "user-abc",
      "unique.app/auth/company-id": "company-xyz",
      "unique.app/chat/chat-id": "chat-123"
    }
  }
}
```

On the server, FastMCP `Depends` extract those values:

```python
from fastmcp.dependencies import Depends
from unique_mcp import get_tool_config, get_unique_settings_async

async def search(
    search_string: str,
    config: SearchToolConfig = Depends(get_tool_config(SearchToolConfig)),
) -> str:
    settings = await get_unique_settings_async()
    ...
```

| Injector | Reads |
| -------- | ----- |
| `get_tool_config(Model)` | `_meta["unique.app/config"]`, else a `UNIQUE_MCP_TOOL_*_CONFIG` env override, else model defaults |
| `get_unique_settings_async()` | JWT / userinfo first; `_meta` auth **only if there is no access token**; chat context whenever `chat-id` is present |
| `get_request_meta()` | The raw `_meta` dict for custom keys |

> **Security:** `_meta` identity is not bound to the bearer token. `unique_mcp` therefore ignores `unique.app/auth/*` as soon as an access token is present. Do not expose `_meta` identity override to untrusted clients. Details: [Per-request identity](../../../unique_mcp/docs/identity.md) and [MCP `_meta`](../../../unique_mcp/docs/meta.md).

## 🗂️ Key prefix

Every Unique key starts with `unique.app/`. The important families:

| Prefix | Typical use |
| ------ | ----------- |
| `unique.app/config-schema` / `unique.app/config` | Admin form on list; saved values on call |
| `unique.app/context-requirements` | Declare required/optional context keys |
| `unique.app/auth/*` | `user-id`, `company-id` |
| `unique.app/chat/*` | `chat-id`, message ids, assistant id |
| `unique.app/icon`, `unique.app/system-prompt`, … | Unique AI presentation |

The full catalogue is in [`unique_mcp/docs/meta.md`](../../../unique_mcp/docs/meta.md#key-catalogue).

## 🔗 Next

- [Agent skill](../../../skills/unique-mcp/) — `npx skills add Unique-AG/ai/skills/unique-mcp`
- [Per-request identity](../../../unique_mcp/docs/identity.md) — token swap and how `_meta` auth ranks against JWT
- [Using MCP Tools in Unique AI](mcp_unique_ai.md) — enabling connectors in a space
- [Unique credentials ↔ Tools](mcp_search.md) — knowledge-base search tutorial
- [Zitadel setup](../../../unique_mcp/docs/zitadel.md) — JWT token type so identity can come from the token instead of `_meta`
