# OneNote MCP Server

Demo MCP server for Microsoft OneNote integration.

> ⚠️ **Single-user auth only** — all connections share one Microsoft account. Not for multi-user production use.

## Tools

| Tool | Description |
|------|-------------|
| `authenticate` | Start device code auth flow |
| `listNotebooks` | List all notebooks |
| `listSections` | List sections in a notebook |
| `listPages` | List pages in a section |
| `getPage` | Get page content |
| `searchPages` | Search pages by keyword |
| `createPage` | Create a new page |
| `appendToPage` | Append content to existing page |

## Local Setup

```bash
cd src
npm install
npm run auth        # Authenticate with Microsoft (device code flow)
npm run start:sse   # Start SSE server on port 3000
```

## Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```
Connect to `http://localhost:3000/sse`

## Authentication

Two ways to authenticate:

1. **Local (before starting):** `npm run auth` — saves token to `.msal-cache.json`
2. **Running server:** Use the `authenticate` MCP tool — prompts device code flow in console

**How tokens work:**
- Access token expires in ~1 hour
- Refresh token valid for 90 days
- MSAL library auto-refreshes using refresh token
- Tokens stored in memory

**Deployed behavior:** Tokens live in container memory. If Azure restarts the container, tokens are lost → re-authenticate via MCP tool. With "Always On" enabled, container stays up but restarts can still happen during maintenance.

## Deploy to Azure

### Prerequisites

1. **Request Azure resources** — Follow [Labs guide](https://unique-ch.atlassian.net/wiki/spaces/DX/pages/1873739786/Labs) to add entry to [environments.yaml](https://github.com/Unique-AG/infrastructure/blob/main/providers/azure/unique-ag/lab/demo/001/config/environments.yaml)
2. **Create `Dockerfile`** — builds container from `src/`, uses `node:20-alpine`, runs `npm run start:sse`
3. **Create `.dockerignore`** — excludes `node_modules`, `.env`, `.msal-cache.json`, `.access-token.txt` (prevents leaking secrets)
4. **Create `deploy.sh`** — Azure CLI script that creates resources and deploys

### What deploy.sh Creates

| Resource | Purpose | Cost |
|----------|---------|------|
| Azure Container Registry (ACR) | Stores Docker images | ~$5/month |
| App Service Plan (B1) | Runs container | ~$13/month |
| Web App | Your MCP server | included |

**Always On** is enabled to prevent idle timeout (20 min without requests would unload the app).

### Deploy

```bash
az login
./deploy.sh
```

### Deployed Instance

- **Azure Portal:** [onenote-mcp-app](https://portal.azure.com/#@unique.ch/resource/subscriptions/698f3b43-ccb0-4f97-9e10-2ca89a7782cf/resourceGroups/rg-lab-demo-001-onenote-mcp/overview)
- **SSE Endpoint:** `https://onenote-mcp-app.azurewebsites.net/sse`

After deployment, authenticate via the `authenticate` MCP tool (check server logs for device code).

### Restart / Clear Auth

To restart the container (clears in-memory tokens):

```bash
az webapp restart -n onenote-mcp-app -g rg-lab-demo-001-onenote-mcp
```

## Connect to Unique Space

After successfull deployment your MCP server is ready to be added to Unique AI using the link you see in Azure + /sse