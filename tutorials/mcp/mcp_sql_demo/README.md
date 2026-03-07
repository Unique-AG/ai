# MCP SQL Demo

A demonstration of an MCP (Model Context Protocol) server that enables natural language queries against a PostgreSQL database. This demo showcases a Portfolio Manager (PM) positions tool that allows users to query investment portfolio data using plain English.

## Overview

This MCP server exposes a tool called `PM_Positions` that:

1. Accepts natural language queries about portfolio positions
2. Uses an LLM (GPT-4o) to convert the query into a valid SQL WHERE clause
3. Executes the query against the database (SQLite or PostgreSQL)
4. Returns results filtered by the authenticated user's email (or a fixed user when `PM_POSITIONS_EMAIL` is set)

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   MCP Client    │────▶│   MCP Server    │────▶│   SQLite or     │
│  (Unique AI)    │     │   (FastMCP)     │     │   PostgreSQL    │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │    Zitadel      │
                        │  (OAuth2/OIDC)  │
                        └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   Unique AI     │
                        │   Gateway       │
                        │  (LLM Access)   │
                        └─────────────────┘
```

## Database

The demo supports two backends, controlled by `DB_TYPE` in the environment:

| `DB_TYPE`  | Use case        | Persistence              |
|------------|------------------|--------------------------|
| `sqlite`   | Default, Azure   | In-memory (re-seeded on restart) |
| `postgres` | Local with Docker| Persistent               |

### SQLite (default)

- No external database. Schema and seed data are in **`src/mcp_sql_demo/sql/create_table_sqlite.sql`**.
- On first request, the app creates an in-memory DB, runs the SQL script (CREATE TABLE + INSERTs), and serves queries.
- On server restart (e.g. redeploy), the DB is recreated and re-seeded from the same file.
- Used by default when running locally (`DB_TYPE=sqlite` in `.env`) and by the Azure deployment.

### PostgreSQL (optional)

For a persistent database, use PostgreSQL and set `DB_TYPE=postgres`.

**Connection details (default):**
- Host: `PGHOST` (default `localhost`)
- Port: `PGPORT` (default `10110`)
- Database: `PGDATABASE` (default `testdb`)
- User: `PGUSER` / Password: `PGPASSWORD`

**Setup:** Create the database (e.g. with `az postgres flexible-server db create` or locally) and run **`src/mcp_sql_demo/sql/create_table_postgres.sql`** to create the table and seed data (idempotent).

### Table schema: `pm_positions`

| Column         | Type          | Description                                                                 |
|----------------|---------------|-----------------------------------------------------------------------------|
| `row_num`      | INT / INTEGER | Primary key                                                                 |
| `sleeve`       | TEXT          | Strategy bucket (e.g. Rates, Equity Long, Alternatives)                    |
| `ticker`       | VARCHAR(10)   | Tradable symbol (e.g. MSFT, SPY)                                            |
| `instrument`   | TEXT          | Security name / description                                                  |
| `direction`    | VARCHAR(5)    | Long or Short                                                               |
| `target_weight`| NUMERIC/REAL  | Intended portfolio weight (e.g. 0.05 = 5%)                                  |
| `position_mm`  | INT           | Position size (e.g. notional in thousands)                                 |
| `email`        | TEXT          | User email for row-level filtering                                          |


To change whose positions are shown to all users, set **`PM_POSITIONS_EMAIL`** (see [Environment variables](#environment-variables)).

## Authentication

### Zitadel OAuth2/OIDC

The MCP server uses **Zitadel** for authentication:

1. **JWT verification** via Zitadel’s JWKS endpoint
2. **OAuth2 proxy** for the authorization flow
3. **User identity** from `{ZITADEL_URL}/oidc/v1/userinfo`

### Row-level filtering by user

- If **`PM_POSITIONS_EMAIL`** is **not** set: queries are filtered by the **authenticated user’s email** from userinfo.
- If **`PM_POSITIONS_EMAIL`** **is** set: all authenticated users see positions for that single email (e.g. `marcluginbuehl@metzler.com`).

### Required scopes

- `mcp:tools`, `mcp:prompts`, `mcp:resources`, `mcp:resource-templates`
- `email`, `openid`, `profile`

## Unique AI integration

| Variable             | Description                          |
|----------------------|--------------------------------------|
| `UNIQUE_SDK_API_BASE`| Unique AI gateway URL                |
| `UNIQUE_SDK_API_KEY` | Unique AI API key                    |
| `UNIQUE_SDK_APP_ID`  | Unique AI application ID             |
| `COMPANY_ID`         | Company context (required for ChatCompletion; missing causes 401) |
| `USER_ID`            | User context (required for ChatCompletion; missing causes 401)   |

The tool uses **Azure GPT-4o** via the Unique AI gateway to turn natural language into a SQL WHERE clause (read-only, schema-aware).

## Environment variables

Create a `.env` file (and/or set in Azure App settings):

```bash
# Database: sqlite (default) or postgres
DB_TYPE=sqlite

# Optional: force all users to see this user's positions
# PM_POSITIONS_EMAIL=your.email@unique.ai

# PostgreSQL (only when DB_TYPE=postgres)
PGHOST=localhost
PGPORT=10110
PGDATABASE=testdb
PGUSER=postgres
PGPASSWORD=postgres

# Zitadel
ZITADEL_URL=https://your-zitadel-instance.com
UPSTREAM_CLIENT_ID=your-client-id
UPSTREAM_CLIENT_SECRET=your-client-secret

# Unique AI
UNIQUE_SDK_API_BASE=https://gateway.unique.app/public/chat-gen2
UNIQUE_SDK_API_KEY=your-api-key
UNIQUE_SDK_APP_ID=your-app-id

# Server
BASE_URL_ENV=https://your-public-url.ngrok-free.app
USER_ID=your-user-id
COMPANY_ID=your-company-id
```

## Setup

### 1. Configure environment

Copy or create `.env` with the variables above. For **SQLite** (default), no database server is required.

### 2. Install dependencies

```bash
uv sync
```

### 3. Run the server

```bash
uv run python src/mcp_sql_demo/mcp_sql_demo.py
```

Server listens on `http://127.0.0.1:8002`.

### Optional: PostgreSQL

If you use `DB_TYPE=postgres`:

```bash
docker compose -f docker_compose.yaml up -d
psql -h localhost -p 10110 -U postgres -f src/mcp_sql_demo/sql/create_table_postgres.sql
```

(Adjust host/port to match `PGHOST` / `PGPORT`.)

## Usage examples

Once connected with an MCP client, you can ask for example:

- "What are my long equity positions?"
- "Show me all positions in the Rates sleeve"

The tool converts these to SQL and returns the matching rows (filtered by user or by `PM_POSITIONS_EMAIL`).

## Query flow

1. **User query:** e.g. "What are my long positions with weight > 5%?"
2. **LLM:** Receives schema and distinct values, returns a WHERE clause.
3. **SQL:** `SELECT * FROM pm_positions WHERE email = ? AND …` (with the generated WHERE).
4. **Response:** Rows are returned (e.g. as a table).

## Dependencies

- `fastmcp` – MCP server framework
- `unique-toolkit` – Unique AI toolkit (LLM, tools)
- `fastapi` – Web framework
- `pydantic` – Data validation
- `psycopg2-binary` – PostgreSQL (only when `DB_TYPE=postgres`)

## Deploy to Azure

### Prerequisites

1. **Azure subscription and resource group** – Already created: subscription `698f3b43-ccb0-4f97-9e10-2ca89a7782cf`, resource group `rg-lab-demo-001-sql-mcp` (see [Labs guide](https://unique-ch.atlassian.net/wiki/spaces/DX/pages/1873739786/Labs) for initial setup).
2. Azure CLI installed and logged in (`az login`)
3. Zitadel app with redirect URI `https://sql-mcp-demo-app.azurewebsites.net/auth/callback`

### What deploy.sh does

- Builds the Docker image in Azure Container Registry
- Creates or updates the Web App (B1 plan)
- Sets app settings: `DB_TYPE=sqlite`, `BASE_URL_ENV`
- Does **not** set `PM_POSITIONS_EMAIL` by default; add it in Azure Portal or via CLI if you want all users to see one user’s positions

### Deploy

```bash
./deploy.sh
```

Then set **required secrets** (Azure Portal or CLI).

```bash
az webapp config appsettings set -n sql-mcp-demo-app -g rg-lab-demo-001-sql-mcp --settings \
  UNIQUE_SDK_API_KEY=<your-api-key> \
  UNIQUE_SDK_APP_ID=<your-app-id> \
  COMPANY_ID=<your-company-id> \
  USER_ID=<your-user-id> \
  ZITADEL_URL=https://id.unique.app \
  UPSTREAM_CLIENT_ID=<your-zitadel-client-id> \
  UPSTREAM_CLIENT_SECRET=<your-zitadel-client-secret>
```

Optional: force a single user’s positions for everyone:

```bash
az webapp config appsettings set -n sql-mcp-demo-app -g rg-lab-demo-001-sql-mcp --settings \
  PM_POSITIONS_EMAIL=marcluginbuehl@metzler.com
```

or just add it in the deploy script (explained in comment)

### Deployed instance

- **Azure Portal:** [sql-mcp-demo-app](https://portal.azure.com/#@unique.ch/resource/subscriptions/698f3b43-ccb0-4f97-9e10-2ca89a7782cf/resourceGroups/rg-lab-demo-001-sql-mcp/overview)
- **MCP endpoint:** `https://sql-mcp-demo-app.azurewebsites.net/mcp`

### Restart

```bash
az webapp restart -n sql-mcp-demo-app -g rg-lab-demo-001-sql-mcp
```

Restarting wipes the in-memory SQLite database; it is re-seeded from `sql/create_table_sqlite.sql` on next use.

## Deploy to Azure with PostgreSQL

This variant deploys a **separate** Web App (`sql-mcp-demo-pg`) and an **Azure Database for PostgreSQL Flexible Server** (Burstable B1ms). The app uses Postgres for both PM data and OAuth client registry, so client IDs persist across restarts and redeploys.

### What deploy_pg.sh does

- Creates **PostgreSQL Flexible Server** and database **only on first run** (idempotent; subsequent runs do not recreate them).
- **Seeds** the `pm_positions` table (required; requires `psql` on PATH).
- Creates or updates the Web App `sql-mcp-demo-pg`, builds the image, and sets app settings (`DB_TYPE=postgres`, `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PG_CLIENT_STORAGE_URL`, `BASE_URL_ENV`).

### Prerequisites

- Same as the SQLite deployment (Azure CLI, subscription, resource group).
- **PostgreSQL admin password** (set `PG_ADMIN_PASSWORD` in env or enter when prompted). Required; the script fails without it.
- **psql** on PATH (PostgreSQL client) to seed the database; the script fails if `psql` is not found.

### Deploy

```bash
./deploy_pg.sh
```

On first run you will be prompted for the PostgreSQL admin password (or set `PG_ADMIN_PASSWORD` in the environment). The script creates the server and database once; on later runs it only rebuilds and redeploys the app.

Then set **required secrets** (same as SQLite deployment, with app name `sql-mcp-demo-pg`).

```bash
az webapp config appsettings set -n sql-mcp-demo-pg -g rg-lab-demo-001-sql-mcp --settings \
  UNIQUE_SDK_API_KEY=... UNIQUE_SDK_APP_ID=... COMPANY_ID=... USER_ID=... \
  ZITADEL_URL=... UPSTREAM_CLIENT_ID=... UPSTREAM_CLIENT_SECRET=...
```

### Environment variables (PostgreSQL deployment)

| Variable | Description |
|----------|-------------|
| `PG_ADMIN_PASSWORD` | PostgreSQL admin password (env or prompt). Required every run so the script can set app settings and run the seed. |
| `PG_CLIENT_STORAGE_URL` | Set by the script. Full Postgres URL for OAuth client registry (asyncpg); must include `?sslmode=require` for Azure. |

### Deployed instance

- **App:** `https://sql-mcp-demo-pg.azurewebsites.net`
- **MCP endpoint:** `https://sql-mcp-demo-pg.azurewebsites.net/mcp`

PostgreSQL server is **not** recreated when you run `deploy_pg.sh` again; only the app image is rebuilt and redeployed.

## Notes

### Client ID / OAuth after redeploy

After a redeploy, the MCP server’s in-memory client registry is cleared. If the client (e.g. Unique AI platform) still uses an old client ID, you may see “Client Not Registered”. **Short-term fix:** In the platform, disconnect or clear auth for this MCP server and connect again so it re-registers. **Long-term fix:** Use the **PostgreSQL deployment** (`deploy_pg.sh`), which persists the OAuth client registry in Postgres so client IDs survive restarts and redeploys.

### Zitadel app configuration

- **App type:** Web Application
- **Token endpoint auth:** POST (`client_secret_post`)
- **Access token type:** JWT (not opaque)
- **Redirect URI:** `https://<your-base-url>/auth/callback`
