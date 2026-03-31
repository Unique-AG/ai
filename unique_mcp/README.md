# unique_mcp

Shared auth and context wiring for [FastMCP](https://github.com/jlowin/fastmcp) servers in the Unique platform. Used as a dependency by MCP servers in this repo to handle per-request authentication against Zitadel and to build `UniqueSettings` / `UniqueServiceFactory` for tool handlers.

---

## Problem → Solution

MCP tools must call Unique APIs on behalf of the requesting user — every tool invocation needs a `UniqueSettings` with the correct `user_id` and `company_id`. Hard-coding a single identity in env vars breaks multi-tenant deployments and leaks credentials.

The MCP server acts as an OAuth proxy: clients receive a FastMCP-issued JWT, which the server swaps server-side for the stored Zitadel token on every request. The Zitadel token _should_ contain `sub` and the company claim, but this depends on token configuration and can't be assumed.

You wire a normal `FastMCP` instance with the Zitadel OAuth proxy (`create_zitadel_oauth_proxy`), then inject **`get_unique_settings`** (and optionally **`get_unique_userinfo`** / **`get_unique_service_factory`**) via `Depends()` into each tool. Those helpers resolve identity per request using a three-priority strategy:

| Priority     | Source                          | Fields                                         | When it wins                                  |
| ------------ | ------------------------------- | ---------------------------------------------- | --------------------------------------------- |
| 1 (highest)  | `_meta` keys in the MCP request | `unique.app/user-id`, `unique.app/company-id`  | Trusted internal callers overriding identity  |
| 2            | Zitadel JWT claims (server-side token swap) | `sub`, `urn:zitadel:iam:user:resourceowner:id` | Normal OAuth flow with fully-configured token |
| 3 (fallback) | Environment-loaded settings     | `UniqueSettings.from_env_auto_with_sdk_init()` | No usable `_meta` or complete JWT claims      |

Both `user-id` and `company-id` must be present for priority 1 or 2 to apply. If JWT claims are incomplete, resolution falls through to env-based auth — `get_unique_settings` does **not** call Zitadel `/userinfo` automatically.

**`get_unique_userinfo`** is a separate async helper: when a Bearer token is present, it performs `GET` on Zitadel’s userinfo endpoint and returns `UniqueUserInfo` (IDs + optional `email`). Use it when you need profile fields or an explicit userinfo round-trip; combine with `get_unique_settings` as needed.

```mermaid
flowchart TD
    A([Tool call arrives]) --> B{_meta contains\nuser-id + company-id?}
    B -- yes --> C[Use _meta identity]
    B -- no --> D{Zitadel JWT has sub\n+ company claim?}
    D -- yes --> E[Use Zitadel JWT claims]
    D -- no --> F[Use env-loaded UniqueSettings auth]
    C & E --> G[Build UniqueSettings → tool executes]
    F --> G
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

Construct the MCP server yourself: `ServerSettings` + `ZitadelOAuthProxySettings`, then `create_zitadel_oauth_proxy`, then register tools that depend on the injectors.

```python
from fastmcp import FastMCP
from fastmcp.dependencies import Depends

from unique_mcp import get_unique_settings, get_unique_service_factory, get_unique_userinfo
from unique_mcp.auth.zitadel.oauth_proxy import (
    ZitadelOAuthProxySettings,
    create_zitadel_oauth_proxy,
)
from unique_mcp.settings import ServerSettings
from unique_toolkit.app.unique_settings import UniqueSettings

server_settings = ServerSettings()
zitadel_settings = ZitadelOAuthProxySettings()

oauth_proxy = create_zitadel_oauth_proxy(
    mcp_server_base_url=server_settings.base_url.encoded_string(),
    zitadel_oauth_proxy_settings=zitadel_settings,
)

mcp = FastMCP("my-server", auth=oauth_proxy)


@mcp.tool()
async def search(query: str, settings: UniqueSettings = Depends(get_unique_settings)) -> str:
    # `settings` carries the correct user_id + company_id for this request
    return await some_unique_api_call(settings, query)


if __name__ == "__main__":
    s = server_settings
    mcp.run(
        transport=s.transport_scheme,
        host=s.local_base_url.host,
        port=s.local_base_url.port,
    )
```

### Public exports (`from unique_mcp import …`)

| Name                         | Role                                                                 |
| ---------------------------- | -------------------------------------------------------------------- |
| `get_unique_settings`        | Sync dependency: returns `UniqueSettings` with per-request auth      |
| `get_unique_service_factory` | Sync dependency: `UniqueServiceFactory` from resolved settings       |
| `get_unique_userinfo`        | Async: Zitadel userinfo → `UniqueUserInfo` (requires access token)   |

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

### 2 — JWT without company claim (env fallback vs userinfo)

If the Zitadel JWT carries `sub` but not the company claim, **`get_unique_settings`** does not apply JWT auth and falls back to **environment** identity from `UniqueSettings.from_env_auto_with_sdk_init()` (typical for local/dev with `UNIQUE_AUTH_*`).

To obtain `sub` + company from Zitadel’s **userinfo** response explicitly, call **`await get_unique_userinfo(http_client)`** in the tool when you need that data (for example email or IDs from userinfo). Configure Zitadel so JWTs embed the resourceowner claim when possible — see [`docs/zitadel/README.md`](docs/zitadel/README.md) — to avoid relying on env or extra calls.

```mermaid
sequenceDiagram
    participant Client
    participant MCP as MCP Server
    participant Zitadel

    Client->>MCP: tools/call + Authorization: Bearer <FastMCP JWT>
    MCP->>MCP: token swap → retrieve Zitadel JWT
    Note over MCP: JWT incomplete for get_unique_settings → env auth
    opt Tool calls get_unique_userinfo
        MCP->>Zitadel: GET /oidc/v1/userinfo (Bearer Zitadel JWT)
        Zitadel-->>MCP: sub, urn:zitadel:...:id, email, ...
    end
    MCP-->>Client: tool result
```

### 3 — Trusted internal caller with `_meta` override

An internal service calls the tool on behalf of a known user by passing identity directly in the MCP `_meta` field. This takes highest priority — but **only works if both `unique.app/user-id` and `unique.app/company-id` are present**. If either is missing, the provider falls through to JWT/env resolution, which will use env auth if the JWT is also incomplete.

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
        MCP->>MCP: build UniqueSettings from _meta (skip JWT/env for auth)
        MCP->>MCP: call Unique API with provided identity
        alt identity is valid
            MCP-->>InternalSvc: tool result
        else user-id or company-id not recognised by Unique
            MCP-->>InternalSvc: error (API rejects identity)
        end
    else _meta incomplete or absent
        MCP->>MCP: fall through to JWT claims / env
        MCP-->>InternalSvc: result or misconfiguration
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

Env-based user/company identity for tools (when JWT/`_meta` do not supply auth) comes from **`unique-toolkit`** / `UniqueSettings.from_env_auto_with_sdk_init()` (for example `UNIQUE_AUTH_*` where applicable in your deployment).

---

## Zitadel setup

See [`docs/zitadel/README.md`](docs/zitadel/README.md) for step-by-step instructions: creating the OAuth app, enabling JWT token type with embedded org claims, configuring redirect URIs (including ngrok for local dev), and required scopes.

---

## Development

```bash
cd unique_mcp && uv run pytest tests/ -q
```
