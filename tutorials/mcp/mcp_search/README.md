# MCP Search Tutorial

A complete tutorial for building and deploying an [MCP](https://modelcontextprotocol.io/) server that exposes Unique's Knowledge Base as a searchable tool. The server uses [FastMCP](https://github.com/jlowin/fastmcp) and authenticates via Zitadel OAuth, making it ready for production use behind HTTPS.

## What You'll Build

An MCP server with a single `search` tool that queries the Unique Knowledge Base using vector, keyword, or combined search. The server:

- Runs on [FastMCP](https://github.com/jlowin/fastmcp) with streamable HTTP transport
- Authenticates users through Zitadel OAuth proxy
- Tags every search result with a document reference (`unique://content/{contentId}`) so any MCP client can cite results and open them in the Unique knowledge base
- Deploys to Azure App Service via [`deploy.sh`](./deploy.sh) (see [Deploy to Azure](#deploy-to-azure)); a Terraform/Container Instances alternative is documented in [DEPLOYMENT.md](./DEPLOYMENT.md)

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   MCP Client    │────▶│   MCP Server    │────▶│  Unique KB API  │
│  (Unique AI)    │     │   (FastMCP)     │     │  (search)       │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │    Zitadel      │
                        │  (OAuth2/OIDC)  │
                        └─────────────────┘
```

## Per-user identity (not a fixed service user)

Search always runs as the **logged-in caller**, not as a shared `UNIQUE_AUTH_*` service account:

| Priority | Source | When |
| -------- | ------ | ---- |
| 1 | MCP `_meta` (`unique.app/auth/user-id` + `company-id`) | Unique AI forwards the chat user's identity |
| 2 | Zitadel JWT claims (`sub` + resourceowner company claim) | OAuth login with a fully configured token |
| 3 | Zitadel `/oidc/v1/userinfo` | JWT is missing the company claim (common) |
| — | Env `UNIQUE_AUTH_*` | **Only** when there is no OAuth session (local unauthenticated dev) |

If a user is logged in but identity cannot be resolved from `_meta` / JWT / userinfo, the tool **errors** instead of falling back to the env service user. See [`src/mcp_search/auth.py`](./src/mcp_search/auth.py).

On Azure, set `UNIQUE_APP_*` / `UNIQUE_API_BASE_URL` for the app’s API credentials. Prefer **not** setting `UNIQUE_AUTH_USER_ID` / `UNIQUE_AUTH_COMPANY_ID` on the Web App so a misconfigured token cannot silently search as one fixed user.

## Document Referencing

Every result returned by the `search` tool carries a stable reference to the source document, on two layers:

**Text layer** — each result is prefixed with a ready-to-paste markdown citation:

```
[Annual Report 2025.pdf](https://next.qa.unique.app/knowledge-upload/scope_…?file=cont_…) (pages 12-14)

<chunk text...>
```

**Structured layer** — each MCP content item carries a `unique.app/reference` entry in its `_meta`, shaped like Unique's `ContentReference` (name, url, sourceId, source, sequenceNumber), so MCP clients can build clickable reference chips without parsing text:

```json
{
  "unique.app/reference": {
    "name": "Annual Report 2025.pdf : 12,13,14",
    "url": "unique://content/cont_abcdefgehijklmnopqrstuvwx",
    "sourceId": "cont_abcdefgehijklmnopqrstuvwx_chunk_abcdefgehijklmnopqrstuv",
    "source": "node-ingestion-chunks",
    "sequenceNumber": 3
  }
}
```

When `UNIQUE_FRONTEND_BASE_URL` is set (e.g. `https://next.qa.unique.app`), result headers use clickable deep links of the form `{base}/knowledge-upload/{scopeId}?file={contentId}` so generic MCP clients like Claude can open the document in the Unique UI. Without that setting (or if the folder/scope cannot be resolved), URLs fall back to `unique://content/{contentId}`, which the Unique platform frontend resolves. External web chunks keep their original `https://` URL. Each result is prefixed with a ready-to-paste markdown citation `[document name](url)`; models are instructed to paste those links inline (never invent `[sourceN]` placeholders) and list them again under Sources. See [`src/mcp_search/references.py`](./src/mcp_search/references.py).

# Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| [Python](https://www.python.org/) | >= 3.12 | Runtime |
| [uv](https://docs.astral.sh/uv/) | latest | Package manager |
| [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) | latest | Azure authentication and resource management |
| [Terraform](https://www.terraform.io/downloads) | >= 1.5.0 | Infrastructure provisioning |
| [Docker](https://docs.docker.com/get-docker/) | latest | Container image builds |

You also need:
- A **Unique platform** account with API credentials
- A **Zitadel** instance with a configured OAuth application
- An **Azure subscription** with permissions to create resources

# Local Development

## 1. Install dependencies

```bash
uv sync
```

## 2. Configure environment

```bash
cp unique.env.example unique.env
cp zitadel.env.example zitadel.env
cp unique_mcp.env.example unique_mcp.env
```

Fill in your credentials in all three files:

**`unique.env`** — your Unique platform credentials:
```
UNIQUE_APP_KEY=<your-app-key>
UNIQUE_APP_ID=<your-app-id>
UNIQUE_API_BASE_URL=https://api.unique.ch
UNIQUE_AUTH_COMPANY_ID=<your-company-id>
UNIQUE_AUTH_USER_ID=<your-user-id>
UNIQUE_APP_ENDPOINT=<your-app-endpoint>
UNIQUE_APP_ENDPOINT_SECRET=<your-endpoint-secret>
```

**`zitadel.env`** — your Zitadel OAuth credentials:
```
ZITADEL_BASE_URL=https://your-instance.zitadel.cloud
ZITADEL_CLIENT_ID=<your-client-id>
ZITADEL_CLIENT_SECRET=<your-client-secret>
```

**`unique_mcp.env`** — MCP server settings:
```
# Public URL clients use to reach the server (for OAuth callbacks, etc.)
# For local dev with ngrok: https://your-subdomain.ngrok-free.app
# Leave unset to default to LOCAL_BASE_URL
UNIQUE_MCP_PUBLIC_BASE_URL=https://your-public-url.example.com

# Local bind address
UNIQUE_MCP_LOCAL_BASE_URL=http://127.0.0.1:8003
```

## 3. Run the server

```bash
# Source your env files
set -a && source unique.env && source zitadel.env && set +a

# Start the server (unique_mcp.env is loaded automatically by the server)
uv run mcp-search
```

The server starts on `http://localhost:8003`. Verify it's running:

```bash
curl http://localhost:8003/health
# {"status": "healthy"}
```

## 4. Test the MCP endpoint

```bash
curl -X POST http://localhost:8003/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "test-client", "version": "1.0"}
    }
  }'
```


## 5. Debug OAuth with the verbose auth client

For end-to-end auth debugging against local or Azure (prints every OAuth HTTP
exchange and decoded JWTs, then lists tools / calls `search`):

```bash
# Against the deployed lab instance (default URL)
uv run python debug_auth_client.py

# Against local server
uv run python debug_auth_client.py --url http://localhost:8003/mcp

# Auth + list_tools only
uv run python debug_auth_client.py --no-search

# Extra FastMCP/httpx logs
uv run python debug_auth_client.py --debug-logs
```

A browser window opens for the MCP consent page → Zitadel login. Tokens are
in-memory only for that process (no Inspector localStorage), so each run starts
a clean Dynamic Client Registration.

There is also a generic discovery script at
[`../client_scripts/debug_mcp_auth.py`](../client_scripts/debug_mcp_auth.py).

## 6. Developing with the MCP Inspector

Start the MCP Inspector against the local streamable HTTP endpoint defined in [`inspector_mcp_server.json`](./inspector_mcp_server.json):

```bash
npx @modelcontextprotocol/inspector --config ./inspector_mcp_server.json --server default-server
```

That config points the client at `http://localhost:8003/mcp` (run `uv run mcp-search` first). The Inspector acts as an MCP client; for OAuth you must register its redirect URI with your IdP (often `http://localhost:6274/oauth/callback` or similar—check the Inspector’s console output).

### `user_id` and `company_id` in tool calls

The Unique stack resolves **user** and **company** for tools from the MCP request. You can supply them in the **`_meta`** object sent with tool invocations, using these keys:

| Key | Purpose |
|-----|---------|
| `unique.app/auth/user-id` | User id |
| `unique.app/auth/company-id` | Company id |

**Both** keys must be set to non-empty strings in `_meta` for that path to apply; otherwise identity falls back to the OAuth token (JWT claims / userinfo) and, when configured, environment variables such as `UNIQUE_AUTH_USER_ID` and `UNIQUE_AUTH_COMPANY_ID`.

See also `MetaKeys` in `unique_mcp` and the example in [`src/mcp_search/mcp_client.py`](./src/mcp_search/mcp_client.py) (`call_tool(..., meta={...})`).



## 7. Connect to the Unique Platform

The Unique platform sends events to your MCP server via a public HTTPS endpoint. During local development you can use [ngrok](https://ngrok.com/) to expose your server.

### Expose the server via ngrok

```bash
ngrok http 8003
```

Copy the generated `https://<subdomain>.ngrok-free.app` URL — this is your **public base URL**.

Set it in `unique_mcp.env`:

```
UNIQUE_MCP_PUBLIC_BASE_URL=https://<subdomain>.ngrok-free.app
```

Traffic flows as: **MCP Client → ngrok → localhost:8003 (MCP Server)**.

### Register the callback URI in Zitadel

Add the ngrok-based redirect URI to your Zitadel OAuth application so the OAuth flow can complete:

```
https://<subdomain>.ngrok-free.app/auth/callback
```

See [`unique_mcp/docs/zitadel/README.md`](../../../unique_mcp/docs/zitadel/README.md) for full Zitadel setup instructions.


# Deploy to Azure

## Prerequisites

1. **Azure subscription and resource group** – Already created: subscription `698f3b43-ccb0-4f97-9e10-2ca89a7782cf` (`lab-demo-001`), resource group `rg-lab-demo-001-unique-search-mcp` (see [Labs guide](https://unique-ch.atlassian.net/wiki/spaces/DX/pages/1873739786/Labs) for initial setup).
2. Azure CLI installed and logged in (`az login`)
3. Zitadel app with redirect URI `https://unique-search-mcp.azurewebsites.net/auth/callback`

## What deploy.sh does

- Creates the **Azure Container Registry** `uniquesearchmcpacr` on first run (idempotent).
- Builds the Docker image in Azure with `az acr build`. The build resolves `unique-mcp` and `unique-toolkit` from PyPI (`uv sync --no-sources`), so it works standalone without the monorepo checkout.
- Creates or updates the **App Service plan** (`unique-search-mcp-plan`, Linux B1) and **Web App** `unique-search-mcp`, and sets `WEBSITES_PORT=8003`, Always On, and the base-URL app settings (`UNIQUE_MCP_LOCAL_BASE_URL`, `UNIQUE_MCP_PUBLIC_BASE_URL`).

## Deploy

```bash
./deploy.sh
```

Then set the **required secrets** (Azure Portal or CLI):

```bash
az webapp config appsettings set -n unique-search-mcp -g rg-lab-demo-001-unique-search-mcp --settings \
  UNIQUE_APP_KEY=<your-app-key> \
  UNIQUE_APP_ID=<your-app-id> \
  UNIQUE_API_BASE_URL=<unique-api-base-url> \
  UNIQUE_APP_ENDPOINT=<your-app-endpoint> \
  UNIQUE_APP_ENDPOINT_SECRET=<your-endpoint-secret> \
  ZITADEL_BASE_URL=<your-zitadel-base-url> \
  ZITADEL_CLIENT_ID=<your-zitadel-client-id> \
  ZITADEL_CLIENT_SECRET=<your-zitadel-client-secret>
```

Do **not** set `UNIQUE_AUTH_USER_ID` / `UNIQUE_AUTH_COMPANY_ID` on the deployed app — those are for local unauthenticated testing only. Production identity comes from the OAuth login (JWT / userinfo) or Unique AI `_meta`.

## Redeploy (code changes only)

```bash
az acr build -t unique-search-mcp:latest -r uniquesearchmcpacr .
az webapp restart -n unique-search-mcp -g rg-lab-demo-001-unique-search-mcp
```

## Deployed instance

- **App:** `https://unique-search-mcp.azurewebsites.net`
- **Health check:** `https://unique-search-mcp.azurewebsites.net/health`
- **MCP endpoint:** `https://unique-search-mcp.azurewebsites.net/mcp`

## Restart

```bash
az webapp restart -n unique-search-mcp -g rg-lab-demo-001-unique-search-mcp
```

Note: OAuth client registrations are kept in memory and are lost on restart — MCP clients will transparently re-register via Dynamic Client Registration.

## Notes

### Zitadel app configuration

- **App type:** Web Application
- **Token endpoint auth:** POST (`client_secret_post`)
- **Access token type:** JWT (not opaque)
- **Redirect URI:** `https://unique-search-mcp.azurewebsites.net/auth/callback`

### Terraform alternative

A full IaC deployment to Azure Container Instances (with Key Vault, Log Analytics, and Caddy-managed HTTPS) is available under [`terraform/`](./terraform/) — see [DEPLOYMENT.md](./DEPLOYMENT.md).


## Further Reading

- [Model Context Protocol specification](https://modelcontextprotocol.io/)
- [FastMCP documentation](https://gofastmcp.com/)
- [Unique Toolkit documentation](https://unique-ag.github.io/ai/)
- [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https)
