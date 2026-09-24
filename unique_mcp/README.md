# unique_mcp

Shared auth and context wiring for [FastMCP](https://github.com/jlowin/fastmcp) servers in the Unique platform. Used as a dependency by MCP servers in this repo to handle per-request authentication against Zitadel and to build `UniqueSettings` / `UniqueServiceFactory` for tool handlers.

Identity is resolved **per request** (JWT claims, then Zitadel `/userinfo`, then `_meta` only when unauthenticated, then env). Admin config and chat context travel in MCP `_meta` under `unique.app/`.

## Documentation

| Page | What it covers |
| ---- | -------------- |
| [Per-request identity](docs/identity.md) | Token swap, resolution order, OAuth scopes, auth scenarios |
| [MCP `_meta` convention](docs/meta.md) | Config schemas, context requirements, and injectors on `tools/call` |
| [Configuration](docs/configuration.md) | Env vars, env files, logging and metrics |
| [Zitadel setup](docs/zitadel.md) | OAuth app, JWT token type, redirect URIs |
| [Docs index](docs/README.md) | All of the above |
| [Agent skill](../skills/unique-mcp/) | Installable Unique MCP best practices (`npx skills add`) |

---

## Usage

Construct the MCP server yourself: `ServerSettings` + `ZitadelOAuthProxySettings`, then `create_zitadel_oauth_proxy`, then register tools that depend on the injectors.

```python
from fastmcp import FastMCP
from fastmcp.dependencies import Depends
from key_value.aio.stores.memory import MemoryStore

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
    client_storage=MemoryStore(),  # swap for shared durable store in prod
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

Prefer **`await get_unique_settings_async()`** in tools that must act as the logged-in user — the sync helper skips `/userinfo` and can fall through to `UNIQUE_AUTH_*`. See [Per-request identity](docs/identity.md).

### Public exports (`from unique_mcp import …`)

| Name                         | Role                                                                 |
| ---------------------------- | -------------------------------------------------------------------- |
| `get_unique_settings`        | Sync: JWT → `_meta` (no token only) → env auth. Prefer the async helper. |
| `get_unique_settings_async`  | JWT → userinfo → `_meta` (no token only); refuses env when logged in |
| `get_unique_service_factory` | Sync `UniqueServiceFactory` from resolved settings                   |
| `get_unique_userinfo`        | Zitadel userinfo → `UniqueUserInfo` (requires access token)          |
| `get_request_meta`           | Raw `_meta` dict of the active request                               |
| `merge_tool_meta`            | Combine a base `_meta` dict with `MetaPart`s for `tools/list`        |
| `ContextRequirements`        | Advertise which context keys the host should send                    |
| `ConfigSchemaMeta`           | Advertise an RJSF config schema for the admin UI                     |
| `get_tool_config`            | `Depends` factory: `_meta` config → env override → model defaults    |
| `UniqueAIToolMeta`           | Advertise Unique AI system-prompt / format-information keys          |
| `MetaKeys`                   | Canonical `unique.app/…` key names                                   |

Identity helpers: [docs/identity.md](docs/identity.md). `_meta` helpers: [docs/meta.md](docs/meta.md).

---

## Development

```bash
cd unique_mcp && uv run pytest tests/ -q
```

Logging, metrics, and env vars: [docs/configuration.md](docs/configuration.md).

## Agent skill (skills.sh)

Codified best practices for agents building Unique MCP servers:

```bash
npx skills add Unique-AG/ai/skills/unique-mcp
```

Source: [`skills/unique-mcp`](../skills/unique-mcp/).
