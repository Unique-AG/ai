# unique_mcp

Shared auth and context wiring for [FastMCP](https://github.com/jlowin/fastmcp) servers in the Unique platform. Used as a dependency by MCP servers in this repo to handle per-request authentication against Zitadel.

---

## Problem → Solution

MCP tools must call Unique APIs on behalf of the requesting user — every tool invocation needs a `UniqueSettings` with the correct `user_id` and `company_id`. Hard-coding a single identity in env vars breaks multi-tenant deployments and leaks credentials.

FastMCP validates the Bearer token but doesn't map it to Unique identities. The JWT _should_ contain `sub` and the Zitadel company claim, but this depends on token configuration and can't be assumed.

**`UniqueContextProvider`** solves this: created once at startup and injected via `Depends()` into each tool, it resolves the right identity per request using a three-priority strategy:

| Priority     | Source                          | Fields                                         | When it wins                                  |
| ------------ | ------------------------------- | ---------------------------------------------- | --------------------------------------------- |
| 1 (highest)  | `_meta` keys in the MCP request | `unique.app/user-id`, `unique.app/company-id`  | Trusted internal callers overriding identity  |
| 2            | JWT claims                      | `sub`, `urn:zitadel:iam:user:resourceowner:id` | Normal OAuth flow with fully-configured token |
| 3 (fallback) | Zitadel `/userinfo` endpoint    | same as JWT                                    | JWT present but claims incomplete             |

Both fields must be present in whichever source wins. If only one is found the provider falls through to the next priority level.

```mermaid
flowchart TD
    A([Tool call arrives]) --> B{_meta contains\nuser-id + company-id?}
    B -- yes --> C[Use _meta identity]
    B -- no --> D{JWT has sub\n+ company claim?}
    D -- yes --> E[Use JWT claims]
    D -- no --> F[GET /oidc/v1/userinfo]
    F --> G{userinfo\ncomplete?}
    G -- yes --> H[Use userinfo]
    G -- no --> I([Raise error])
    C & E & H --> J([Build UniqueSettings → tool executes])
```

### OAuth scopes

The OAuthProxy advertises these valid scopes:

| Scope                                | Purpose                            |
| ------------------------------------ | ---------------------------------- |
| `openid`                             | Base OIDC scope                    |
| `profile`                            | Name and basic profile claims      |
| `email`                              | Email claim                        |
| `urn:zitadel:iam:user:resourceowner` | Embeds company/org ID in the token |
| `mcp:tools`                          | Access to MCP tools                |
| `mcp:prompts`                        | Access to MCP prompts              |
| `mcp:resources`                      | Access to MCP resources            |
| `mcp:resource-templates`             | Access to MCP resource templates   |

---

## Usage

```python
from fastmcp.server.dependencies import Depends
from unique_mcp.server import create_unique_mcp_server

bundle = create_unique_mcp_server("my-server")
mcp = bundle.mcp
provider = bundle.context_provider


@mcp.tool()
async def search(query: str, settings=Depends(provider.get_settings)) -> str:
    # `settings` carries the correct user_id + company_id for this request
    return await some_unique_api_call(settings, query)


if __name__ == "__main__":
    s = bundle.server_settings
    mcp.run(
        transport=s.transport_scheme,
        host=s.local_base_url.host,
        port=s.local_base_url.port,
    )
```

`create_unique_mcp_server()` returns an `UniqueMCPServerBundle`:

| Field              | Type                    | Purpose                               |
| ------------------ | ----------------------- | ------------------------------------- |
| `mcp`              | `FastMCP`               | Server instance — register tools here |
| `context_provider` | `UniqueContextProvider` | Per-request auth resolver             |
| `server_settings`  | `ServerSettings`        | Transport/URL config                  |

`UniqueContextProvider` exposes three async methods:

```python
settings = await provider.get_settings()   # UniqueSettings (app + api config + auth)
context  = await provider.get_context()    # UniqueContext (auth only, lighter weight)
info     = await provider.get_userinfo()   # Raw Zitadel userinfo (email, name, etc.)
```

---

## Scenarios

### 1 — Normal OAuth flow (JWT with full claims)

The common case. Zitadel issues a JWT with `sub` and `urn:zitadel:iam:user:resourceowner:id` embedded. The provider reads them directly from the verified token — no extra network call needed.

```mermaid
sequenceDiagram
    participant Client
    participant MCP as MCP Server
    participant Zitadel

    Client->>Zitadel: OAuth flow (authorize + token)
    Zitadel-->>Client: JWT (sub + urn:zitadel:...:id in claims)
    Client->>MCP: POST /tools/call + Authorization: Bearer JWT
    MCP->>MCP: verify signature, extract claims
    MCP->>MCP: build UniqueSettings
    MCP-->>Client: tool result
```

### 2 — JWT without company claim (userinfo fallback)

The default for newly registered Zitadel apps until the JWT action is configured. The JWT carries `sub` but no company claim, so the provider falls back to `/userinfo`. This adds one HTTP round-trip per request; avoid it by configuring Zitadel to embed the `urn:zitadel:iam:user:resourceowner` scope in the JWT — see [`docs/zitadel/README.md`](docs/zitadel/README.md).

```mermaid
sequenceDiagram
    participant MCP as MCP Server
    participant Zitadel

    Note over MCP: JWT has sub but no company_id claim
    MCP->>Zitadel: GET /oidc/v1/userinfo (Bearer JWT)
    Zitadel-->>MCP: sub, urn:zitadel:...:id, email, ...
    MCP->>MCP: extract sub + company_id, build UniqueSettings
```

### 3 — Trusted internal caller with `_meta` override

An internal service calls the tool on behalf of a known user by passing identity directly in the MCP `_meta` field. This takes highest priority and bypasses JWT/userinfo resolution entirely.

> **Security:** The server takes `_meta` values as-is without further validation. Only use this from callers you fully trust — never expose it to external users.

```json
{
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": { "query": "hello" },
    "_meta": {
      "unique.app/user-id": "user-abc123",
      "unique.app/company-id": "company-xyz456"
    }
  }
}
```

```mermaid
sequenceDiagram
    participant InternalSvc as Internal Service
    participant MCP as MCP Server

    InternalSvc->>MCP: tools/call + _meta (user-id + company-id)
    Note over MCP: _meta present → skip JWT + userinfo
    MCP->>MCP: build UniqueSettings from _meta
    MCP-->>InternalSvc: tool result
```

---

## Configuration

**`UNIQUE_MCP_*`** — server settings:

| Variable                     | Default                 | Purpose                                 |
| ---------------------------- | ----------------------- | --------------------------------------- |
| `UNIQUE_MCP_PUBLIC_BASE_URL` | _(none)_                | Public URL advertised in OAuth metadata |
| `UNIQUE_MCP_LOCAL_BASE_URL`  | `http://localhost:8003` | Bind address                            |

**`ZITADEL_*`** — OAuth proxy settings:

| Variable                | Default                  | Purpose              |
| ----------------------- | ------------------------ | -------------------- |
| `ZITADEL_BASE_URL`      | `http://localhost:10116` | Zitadel instance URL |
| `ZITADEL_CLIENT_ID`     | _(required in prod)_     | OAuth client ID      |
| `ZITADEL_CLIENT_SECRET` | _(required in prod)_     | OAuth client secret  |

---

## Zitadel setup

See [`docs/zitadel/README.md`](docs/zitadel/README.md) for step-by-step instructions: creating the OAuth app, enabling JWT token type with embedded org claims, configuring redirect URIs (including ngrok for local dev), and required scopes.

---

## Development

```bash
cd unique_mcp && uv run pytest tests/ -q
```
