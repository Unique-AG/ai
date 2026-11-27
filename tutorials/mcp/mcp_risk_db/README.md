# Risk Database MCP Server

Demo MCP server that exposes a bundled Excel risk database as read-only tools. The server keeps Excel as the source of truth, loads it with pandas, and protects remote access with Zitadel OAuth.

## Business goal

This demo mocks a real risk database in Excel, making the data simple for Sales to inspect and update while AI assistants gain structured access through MCP.

Users can ask natural-language questions across the workbook, while the assistant discovers the available sheets and calls deterministic query tools.

## Data

The workbook simulates risk management for a multi-strategy hedge fund. Risk and compliance teams use this type of data to identify limit breaches, warning levels, concentrated positions, liquidity concerns, and performance changes.

Important sheets include:

- `positions`: holdings, exposure, P&L, liquidity, analyst, and strategy.
- `risk_limits`: utilization, warning thresholds, and breach flags.
- `var_stress`: potential losses under risk scenarios.
- `liquidity` and `crowding`: positions that may be difficult to exit.
- `pnl_daily`: daily and year-to-date performance.
- `schema`: metadata describing the available tables.

The source file is `data/risk_database.xlsx`.

## How it works

1. At startup, `server.py` loads every Excel sheet into a pandas `DataFrame`.
2. FastMCP exposes two read-only tools over the in-memory data.
3. When PostgreSQL is configured, the sheets are also mirrored into database tables for demonstration and inspection. MCP tools continue to query pandas.
4. FastMCP `OAuthProxy` delegates authentication to Zitadel and verifies access tokens through introspection.
5. Dynamic MCP client registrations use a local file store during development and PostgreSQL in Azure.
6. The server exposes Streamable HTTP at `/mcp` and a health endpoint at `/`.

### Main files

- `server.py`: data loading, PostgreSQL mirroring, OAuth, tools, and HTTP server.
- `data/risk_database.xlsx`: source workbook.
- `.env.example`: local and deployment configuration.
- `pyproject.toml` and `uv.lock`: Python dependencies and resolved versions.
- `Dockerfile`: Azure App Service container.
- `deploy.sh`: Azure resource provisioning and deployment.
- `.cursor/skills/update-excel/SKILL.md`: workbook update workflow.

### Endpoints

| URL | Purpose |
|-----|---------|
| `https://<host>/mcp` | MCP Streamable HTTP endpoint |
| `https://<host>/` | Health JSON |

### Tools

| Tool | Description |
|------|-------------|
| `get_schema` | Lists sheets, columns, row counts, primary keys, and samples |
| `query_data` | Queries a sheet with filters, column selection, and a row limit |

## Run locally and test with MCP Inspector

1. Create `.env` from the example and configure the Zitadel client:

   ```bash
   cp .env.example .env
   ```

2. Install the locked dependencies and start the server:

   ```bash
   uv sync
   uv run server.py
   ```

3. In another terminal, start MCP Inspector:

   ```bash
   npx @modelcontextprotocol/inspector
   ```

4. Connect with:
   - Transport: **Streamable HTTP**
   - URL: `http://127.0.0.1:8002/mcp`

5. Call `get_schema`, then test `query_data`:

   ```json
   {
     "sheet_name": "positions",
     "filters": {
       "sector": "Technology"
     },
     "limit": 10
   }
   ```

Local OAuth client registrations are persisted under `.local/oauth-client-store`, so they survive server restarts. PostgreSQL is not needed locally unless the database mirror is part of the demonstration.

## Authentication with Zitadel

The server uses FastMCP `OAuthProxy` with Zitadel:

- Authorization code flow with PKCE protects the browser authorization exchange.
- `IntrospectionTokenVerifier` calls `{ZITADEL_URL}/oauth/v2/introspect` to validate access tokens.
- The proxy forwards authorization, token, and revocation operations to Zitadel.
- Scopes limit the capabilities that clients can request.
- The Zitadel application client ID and secret identify this MCP to Zitadel.
- Dynamic client registrations identify MCP clients such as Unique AI. They are separate from the Zitadel application client ID.

### Create the Zitadel application

1. Open the Zitadel Console and select the organization and project used for MCP applications.
2. Create a **Web** application named, for example, `risk-database-mcp`.
3. Set token endpoint authentication to **Post** (`client_secret_post`).
4. Set the access token type to **JWT**.
5. Add each server callback URL:
   - Local tunnel: `https://<public-host>/auth/callback`
   - Azure: `https://<app-name>.azurewebsites.net/auth/callback`
6. Save the application and copy its client ID and secret into `.env`:

   ```env
   ZITADEL_URL=https://id.unique.app
   UPSTREAM_CLIENT_ID=<client-id>
   UPSTREAM_CLIENT_SECRET=<client-secret>
   ```

## Expose the local server and connect it to Unique AI

1. Start the server with its public origin:

   ```bash
   uv run server.py https://<public-host>
   ```

2. Expose port `8002`:

   ```bash
   ngrok http 8002 --url https://<public-host>
   ```

3. Add `https://<public-host>/auth/callback` to the Zitadel application.
4. Add the MCP in Unique AI:
   - URL: `https://<public-host>/mcp`
5. Authorize the connection and attach the MCP to a space.

Example questions:

- `Identify all hard risk-limit breaches and warnings across every fund.`
- `Which positions have critical crowding or are flagged as illiquid?`
- `Summarize the latest P&L and main risk exposures for each fund.`

## Deploy to Azure

### Prerequisites

1. Request a lab subscription and resource group through an infrastructure PR. Add the environment to `providers/azure/unique-ag/lab/demo/001/config/environments.yaml`; see the [Labs guide](https://unique-ch.atlassian.net/wiki/spaces/DX/pages/1873739786/Labs).
2. Install Azure CLI and authenticate with `az login`.
3. Configure the production callback URL in Zitadel.
4. Set `PG_ADMIN_PASSWORD`, `UPSTREAM_CLIENT_ID`, and `UPSTREAM_CLIENT_SECRET` in `.env`.

### What `deploy.sh` does

- Selects the configured Azure subscription.
- Creates PostgreSQL Flexible Server and the database on the first run.
- Builds the container in Azure Container Registry.
- Creates or updates the App Service plan and Web App.
- Configures PostgreSQL, OAuth, port, and public URL application settings.
- Removes the legacy `PG_CLIENT_STORAGE_URL` setting; the server safely builds its connection from the discrete `PG*` settings.

### Deploy or redeploy

```bash
./deploy.sh
az webapp restart -n risk-db-mcp-app -g rg-lab-demo-001-risk-db-mcp
```

The PostgreSQL server is created only once. Later runs rebuild the image and update the Web App.

Current demo endpoints:

- Health: `https://risk-db-mcp-app.azurewebsites.net/`
- MCP: `https://risk-db-mcp-app.azurewebsites.net/mcp`

Connect the deployed endpoint to Unique AI using the same process as the ngrok endpoint.

### Logs

For live output, open the Web App in Azure Portal and select **Monitoring → Log stream**.

The `risk-db-mcp-logs` diagnostic setting forwards HTTP, console, and platform logs to `law-lab-demo-001-shared`. In that Log Analytics workspace, run:

```kusto
AppServiceConsoleLogs
| where _ResourceId endswith "/risk-db-mcp-app"
| where TimeGenerated > ago(1h)
| project TimeGenerated, Level, Message=ResultDescription
| order by TimeGenerated desc
```

### PostgreSQL mirror

On startup, the server replaces one PostgreSQL table per workbook sheet. This mirror is for database inspection only; MCP queries continue to use pandas.

To showcase the mirrored data after deployment, create a **PostgreSQL** connection in TablePlus with:

| Field | Value |
|-------|-------|
| Name | `risk-db-azure` |
| Host | `risk-db-mcp-pg-db.postgres.database.azure.com` |
| Port | `5432` |
| User | `pgadmin` |
| Password | `PG_ADMIN_PASSWORD` from `.env` |
| Database | `riskdb` |
| SSL mode | Required |

Test the connection, connect, and open the mirrored sheet tables.

## Update data in Excel

Use `.cursor/skills/update-excel/SKILL.md` to replace the workbook, review schema changes, redeploy, and verify the updated data.
