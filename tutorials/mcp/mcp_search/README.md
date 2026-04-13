# MCP Search Tutorial

A complete tutorial for building and deploying an [MCP](https://modelcontextprotocol.io/) server that exposes Unique's Knowledge Base as a searchable tool. The server uses [FastMCP](https://github.com/jlowin/fastmcp) and authenticates via Zitadel OAuth, making it ready for production use behind HTTPS.

## What You'll Build

An MCP server with a single `search` tool that queries the Unique Knowledge Base using vector, keyword, or combined search. The server:

- Runs on [FastMCP](https://github.com/jlowin/fastmcp) with streamable HTTP transport
- Authenticates users through Zitadel OAuth proxy
- Deploys to Azure Container Instances with automatic HTTPS via Caddy
- Stores secrets in Azure Key Vault and logs in Log Analytics

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


## 5. Developing with the MCP Inspector

Start the official mcp inspector using 

```
npx @modelcontextprotocol/inspector
```

The MCP Inspector act as an MCP Client, there if you want to authenticate we must register its redirect URI (usually http://localhost:6247/oauth/callback) on our IDP (in this case Zitadel).



## 6. Connect to the Unique Platform

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


## Further Reading

- [Model Context Protocol specification](https://modelcontextprotocol.io/)
- [FastMCP documentation](https://gofastmcp.com/)
- [Unique Toolkit documentation](https://unique-ag.github.io/ai/)
- [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https)
