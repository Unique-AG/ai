# unique_mcp

Shared auth and context wiring for [FastMCP](https://github.com/jlowin/fastmcp) servers in the Unique platform. Used as a dependency by MCP servers in this repo to handle per-request authentication against Zitadel.

---

## Problem → Solution

MCP tools must call Unique APIs on behalf of the requesting user — every tool invocation needs a `UniqueSettings` with the correct `user_id` and `company_id`. Hard-coding a single identity in env vars breaks multi-tenant deployments and leaks credentials.

The MCP server acts as an OAuth proxy: clients receive a FastMCP-issued JWT, which the server swaps server-side for the stored Zitadel token on every request. The Zitadel token _should_ contain `sub` and the company claim, but this depends on token configuration and can't be assumed.

**`UniqueContextProvider`** solves this: created once at startup and injected via `Depends()` into each tool, it resolves the right identity per request using a three-priority strategy:

| Priority     | Source                          | Fields                                         | When it wins                                  |
| ------------ | ------------------------------- | ---------------------------------------------- | --------------------------------------------- |
| 1 (highest)  | `_meta` keys in the MCP request | `unique.app/user-id`, `unique.app/company-id`  | Trusted internal callers overriding identity  |
| 2            | Zitadel JWT claims (server-side token swap) | `sub`, `urn:zitadel:iam:user:resourceowner:id` | Normal OAuth flow with fully-configured token |
| 3 (fallback) | Zitadel `/userinfo` endpoint    | same as JWT                                    | JWT present but claims incomplete             |

Both fields must be present in whichever source wins. If only one is found the provider falls through to the next priority level.

```mermaid
flowchart TD
    A([Tool call arrives]) --> B{_meta contains\nuser-id + company-id?}
    B -- yes --> C[Use _meta identity]
    B -- no --> D{Zitadel JWT has sub\n+ company claim?}
    D -- yes --> E[Use Zitadel JWT claims]
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

The common case. The MCP server acts as an OAuth Authorization Server and proxies the login to Zitadel using the **token swap pattern**:

1. The client authenticates against the MCP server's OAuth endpoints (not Zitadel directly).
2. The MCP server proxies to Zitadel, obtains a Zitadel token, and stores it server-side.
3. The MCP server issues its own short-lived **FastMCP JWT** to the client.
4. On every tool call, the MCP server swaps the FastMCP JWT for the stored Zitadel token, validates it against Zitadel's JWKS, and extracts claims — no extra network call needed when the Zitadel JWT contains `sub` + `urn:zitadel:iam:user:resourceowner:id`.

```mermaid
sequenceDiagram
    participant Client
    participant MCP as MCP Server
    participant Zitadel

    Client->>MCP: GET /.well-known/oauth-authorization-server
    MCP-->>Client: OAuth metadata (authorize/token endpoints)
    Client->>MCP: GET /authorize
    MCP->>Zitadel: redirect (proxy OAuth flow)
    Zitadel-->>Client: login page
    Client->>Zitadel: authenticate
    Zitadel-->>MCP: authorization code (callback)
    MCP->>Zitadel: POST /oauth/v2/token (exchange code)
    Zitadel-->>MCP: Zitadel JWT (stored server-side, never sent to client)
    MCP-->>Client: FastMCP JWT (reference token)

    Client->>MCP: tools/call + Authorization: Bearer <FastMCP JWT>
    MCP->>MCP: verify FastMCP JWT signature → look up JTI → retrieve stored Zitadel JWT
    MCP->>MCP: validate Zitadel JWT via JWKS, extract sub + company_id claims
    MCP->>MCP: build UniqueSettings
    MCP-->>Client: tool result
```

### 2 — JWT without company claim (userinfo fallback)

The default for newly registered Zitadel apps until the JWT action is configured. The Zitadel JWT carries `sub` but no company claim, so the provider falls back to `/userinfo`. This adds one HTTP round-trip per request; avoid it by configuring Zitadel to embed the `urn:zitadel:iam:user:resourceowner` scope in the JWT — see [`docs/zitadel/README.md`](docs/zitadel/README.md).

```mermaid
sequenceDiagram
    participant MCP as MCP Server
    participant Zitadel

    Note over MCP: Zitadel JWT has sub but no company_id claim
    MCP->>Zitadel: GET /oidc/v1/userinfo (Bearer Zitadel JWT)
    Zitadel-->>MCP: sub, urn:zitadel:...:id, email, ...
    MCP->>MCP: extract sub + company_id, build UniqueSettings
```

### 3 — Trusted internal caller with `_meta` override

An internal service calls the tool on behalf of a known user by passing identity directly in the MCP `_meta` field. This takes highest priority — but **only works if both `unique.app/user-id` and `unique.app/company-id` are present**. If either is missing, the provider falls through to JWT/userinfo resolution, which will fail if no valid Bearer token is present.

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

    InternalSvc->>MCP: tools/call + Bearer <token> + _meta
    MCP->>MCP: verify Bearer token (transport-level auth)
    alt _meta has both user-id + company-id
        MCP->>MCP: build UniqueSettings from _meta (skip JWT/userinfo)
        MCP->>MCP: call Unique API with provided identity
        alt identity is valid
            MCP-->>InternalSvc: tool result
        else user-id or company-id not recognised by Unique
            MCP-->>InternalSvc: error (API rejects identity)
        end
    else _meta incomplete or absent
        MCP->>MCP: fall through to JWT claims / userinfo
        Note over MCP: fails if token missing or claims incomplete
        MCP-->>InternalSvc: error
    end
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
