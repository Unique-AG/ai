# Configuration

`unique_mcp` loads settings from the process environment and from env files next to the working directory (`unique_mcp.env` / `.env` for server settings, `zitadel.env` / `.env` for the OAuth proxy). See [`find_env_file`](../src/unique_mcp/util/find_env_file.py).

---

## Server (`UNIQUE_MCP_*`)

`ServerSettings` (`unique_mcp.settings`).

| Variable                     | Default                 | Purpose                                 |
| ---------------------------- | ----------------------- | --------------------------------------- |
| `UNIQUE_MCP_PUBLIC_BASE_URL` | _(none)_                | Public URL advertised in OAuth metadata |
| `UNIQUE_MCP_LOCAL_BASE_URL`  | `http://localhost:8003` | Bind address                            |

`base_url` is `PUBLIC_BASE_URL` if set, otherwise `LOCAL_BASE_URL`. That value is what you pass to `create_zitadel_oauth_proxy(..., mcp_server_base_url=...)`.

## Zitadel OAuth proxy (`ZITADEL_*`)

`ZitadelOAuthProxySettings`. Required in production; defaults are local-dev placeholders.

| Variable                | Default                  | Purpose              |
| ----------------------- | ------------------------ | -------------------- |
| `ZITADEL_BASE_URL`      | `http://localhost:10116` | Zitadel instance URL |
| `ZITADEL_CLIENT_ID`     | _(required in prod)_     | OAuth client ID      |
| `ZITADEL_CLIENT_SECRET` | _(required in prod)_     | OAuth client secret  |

App registration and token type: [Zitadel setup](zitadel.md).

## Unique toolkit identity (`UNIQUE_AUTH_*` / `UNIQUE_APP_*`)

Env-based user/company identity for tools (when JWT/`_meta` do not supply auth) comes from **`unique-toolkit`** / `UniqueSettings.from_env_auto_with_sdk_init()` (for example `UNIQUE_AUTH_*` where applicable in your deployment). API credentials (`UNIQUE_APP_*`, `UNIQUE_API_BASE_URL`) are still required so the SDK can call Unique APIs.

On multi-user servers, prefer **not** setting `UNIQUE_AUTH_USER_ID` / `UNIQUE_AUTH_COMPANY_ID` so an incomplete token cannot silently run as one fixed user. See [Per-request identity](identity.md).

## Tool config overrides (`UNIQUE_MCP_TOOL_*`)

When the host does not inject `unique.app/config` on `tools/call`, `get_tool_config` reads a JSON override from:

```
UNIQUE_MCP_TOOL_{SERVER}_{CONFIG}_CONFIG
```

Example: FastMCP server name `mcp-search` + model `SearchToolConfig` → `UNIQUE_MCP_TOOL_MCP_SEARCH_SEARCH_TOOL_CONFIG`. Details: [MCP `_meta` — config](meta.md#config-uniqueappconfig).

---

## Logging and metrics

On import, `unique_mcp` sets `FASTMCP_CHECK_FOR_UPDATES=off` (unless already set). Call `configure_tracing` from `unique-toolkit[otel]` when you want Tempo/OTLP export.

```python
from unique_toolkit.monitoring import configure_tracing
from unique_mcp.logging import configure_logging
from unique_mcp.monitoring import setup_ops

configure_tracing(service_name="my-mcp")
configure_logging()

mcp = FastMCP("my-server")
middleware = [...]
middleware.append(setup_ops(mcp))

mcp.run(transport="http", middleware=middleware)
```
