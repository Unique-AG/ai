# Risk Database MCP Server

Read-only MCP server over a bundled Excel risk database. Tools (`get_schema`, `query_data`) use **pandas / Excel** in memory. When **PostgreSQL** is configured, the same data is **mirrored into tables** on startup for demos (e.g. TablePlus). **Zitadel OAuth** protects the MCP HTTP endpoint.

## Endpoints

| URL | Purpose |
|-----|---------|
| `https://<host>/mcp` | MCP (streamable HTTP) — use this in Unique AI MCP Hub |
| `https://<host>/` | Health JSON |

**Azure example:** `https://risk-db-mcp-app.azurewebsites.net/mcp`

## Tools

| Tool | Description |
|------|-------------|
| `get_schema` | List sheets with columns, row counts, sample rows |
| `query_data` | Query a sheet with optional filters, column selection, limit |

## Authentication (Zitadel)

The server uses **FastMCP `OAuthProxy`** with **Zitadel** as the identity provider:

1. JWT verification via Zitadel JWKS (`{ZITADEL_URL}/oauth/v2/keys`)
2. OAuth2 authorization code flow with PKCE
3. **OAuth client registrations** for MCP clients are stored in **PostgreSQL** (`py-key-value-aio` `PostgreSQLStore`) when Postgres is configured, so client IDs survive app restarts and redeploys. Without Postgres, an in-memory store is used (local dev only).

### Required OAuth scopes

Configure these on the Zitadel application (or ensure they can be requested):

- `mcp:tools`, `mcp:prompts`, `mcp:resources`, `mcp:resource-templates`
- `email`, `openid`, `profile`

### Zitadel application setup (step by step)

Use the **same Zitadel organization/project** as the MCP SQL demo, but create a **new application** (separate client ID and secret).

1. Open **Zitadel Console**: [https://id.unique.app](https://id.unique.app) and sign in with an admin account.
2. Open **Projects** and select the project used for **MCP SQL demo** (or your team’s MCP demos project).
3. Under **Applications**, click **New**.
4. Choose **Web** application (or **User Agent** flow compatible with web redirect — same pattern as MCP SQL demo).
5. Set a name, e.g. `risk-database-mcp`.
6. **Authentication method** for the token endpoint: **Post** (`client_secret_post`).
7. **Redirect URIs** — add exactly (production):

   `https://risk-db-mcp-app.azurewebsites.net/auth/callback`

   For local testing with a public URL (e.g. ngrok), add:

   `https://<your-subdomain>.ngrok-free.app/auth/callback`

8. **Access token type**: **JWT** (not opaque).
9. Save the application. Copy:
   - **Client ID**
   - **Client secret** (shown at creation; store it securely — it may not be shown again).

### Set client ID and secret in Azure App Service

After `./deploy.sh`, set the OAuth credentials as **application settings** (slot settings if you use slots):

```bash
az webapp config appsettings set \
  -n risk-db-mcp-app \
  -g rg-lab-demo-001-risk-db-mcp \
  --settings \
    UPSTREAM_CLIENT_ID='<paste-client-id>' \
    UPSTREAM_CLIENT_SECRET='<paste-client-secret>'
```

**Azure Portal:** App Service → **Configuration** → **Application settings** → **New application setting**:

- Name: `UPSTREAM_CLIENT_ID`, Value: (client ID)
- Name: `UPSTREAM_CLIENT_SECRET`, Value: (client secret) — mark as **Deployment slot setting** if needed

Then **Save** and restart the app if prompted.

## PostgreSQL mirror (showcase only)

- On startup, after loading Excel into pandas, the server **drops and recreates** mirror tables in Postgres (one table per sheet; names sanitized, e.g. lowercase, spaces → `_`).
- **MCP tools do not query Postgres**; they keep using Excel/pandas.
- Sync runs on every process start (including after deploy), so the mirror matches the bundled workbook.

## TablePlus / SQL client (read-only browsing)

Use the Flexible Server created by `deploy.sh`:

| Field | Value |
|-------|--------|
| Host | `risk-db-mcp-pg-db.postgres.database.azure.com` (FQDN from Azure Portal → PostgreSQL server → **Overview**) |
| Port | `5432` |
| Database | `riskdb` |
| User | `pgadmin` (or `PG_ADMIN_USER` if you changed it) |
| Password | The same `PG_ADMIN_PASSWORD` you used when running `deploy.sh` |
| SSL | **Required** |

Example sheet-backed tables (after first app start): `positions`, `exposures`, `pnl_daily`, `factor_risk`, `var_stress`, `liquidity`, `risk_limits`, `drawdowns`, `counterparty`, `performance`, `events_calendar`, `crowding`, `correlations`, `greeks`, `redemption_liquidity`, `schema` (exact names depend on sanitization of Excel sheet names).

## Local run

```bash
uv sync
cp .env.example .env
# Edit .env: BASE_URL_ENV, ZITADEL_URL, UPSTREAM_CLIENT_ID, UPSTREAM_CLIENT_SECRET
uv run server.py
```

Default: `http://127.0.0.1:8002/mcp` (no Postgres unless you configure the `PG*` variables).

## Deploy to Azure

### Prerequisites

1. **Azure subscription and resource group** — Request a lab environment through an infrastructure PR by adding an entry to `providers/azure/unique-ag/lab/demo/001/config/environments.yaml`. See the [Labs guide](https://unique-ch.atlassian.net/wiki/spaces/DX/pages/1873739786/Labs) for the process.

   This demo uses subscription `698f3b43-ccb0-4f97-9e10-2ca89a7782cf` and resource group `rg-lab-demo-001-risk-db-mcp`.
2. **Azure CLI** installed and authenticated with `az login`.
3. **Zitadel application** configured as described above, including redirect URI `https://risk-db-mcp-app.azurewebsites.net/auth/callback`.

### What `deploy.sh` does

- Selects the Azure subscription.
- Creates the PostgreSQL Flexible Server and database on the first run.
- Builds the container image in Azure Container Registry.
- Creates or updates the App Service plan and Web App.
- Configures the Postgres, OAuth, port, and public base URL application settings.

### Deploy

1. Export or enter the Postgres admin password:

   ```bash
   export PG_ADMIN_PASSWORD='your-secure-password'
   ```

2. From this directory:

   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. Set Zitadel secrets (see above).

4. Restart the Web App after deployment so it starts with the latest container image and settings:

   ```bash
   az webapp restart -n risk-db-mcp-app -g rg-lab-demo-001-risk-db-mcp
   ```

The script creates the Postgres server **once** (idempotent); later runs rebuild the container and update settings.

### Deployed instance

- Health: `https://risk-db-mcp-app.azurewebsites.net/`
- MCP: `https://risk-db-mcp-app.azurewebsites.net/mcp`

Connect it to Unique AI in the same way as the ngrok deployment, using the deployed MCP URL.

### Logs

For live output, open the Web App in Azure Portal and select **Monitoring → Log stream**.

The Web App also has a diagnostic setting named `risk-db-mcp-logs`, configured separately from `deploy.sh`. It forwards **HTTP**, **console**, and **platform** logs to the shared Log Analytics workspace `law-lab-demo-001-shared`.

## Example prompts (Unique AI)

- What sheets are in the risk database? Show the schema.
- Show long positions in the Technology sector.
- Which tickers have CRITICAL crowding tier?
- Show risk limits that are breached.

## Data

Workbook: `data/risk_database.xlsx`. Replace the file and redeploy to refresh; Postgres mirror updates on next startup.
