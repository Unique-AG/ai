# MCP Trade Reconciliation

An MCP (Model Context Protocol) server that reconciles **counterparty (email) cash flows** against **customer (book) cash flows** stored in PostgreSQL. It exposes deterministic, SQL-backed tools (no LLM in the loop) that an MCP client such as Unique AI can call to read, save, and reconcile cash flows.

This tutorial was split out of the [`mcp_sql_demo`](../mcp_sql_demo) example, which keeps the natural-language *PM positions* tool. This project focuses solely on trade reconciliation.

## Overview

The reconciliation problem: each day our trading book produces internal trades (**customer book cash flows**), and counterparties send emails (settlement instructions, confirmations) from which we extract **counterparty email cash flows**. We need to determine which email cash flow corresponds to which book cash flow.

The server exposes four tools:

| Tool | Purpose |
|------|---------|
| `Get_Customer_Book_Cashflows` | Read internal book cash flows, with optional filters. |
| `Get_Counterparty_Email_Cashflows` | Read counterparty (email) cash flows, with optional filters. |
| `Match_Cashflows` | Reconcile UNMATCHED email rows against the book; returns a reason per row. |
| `Save_Counterparty_Email_Cashflow` | Insert a new email cash flow and immediately attempt to match it. |
| `Reset_Demo_Data` | Restore both tables to the seed baseline (all email rows back to UNMATCHED). Destructive; intended for demos. |

### Matching rules

A counterparty (email) row matches a customer (book) row when **all** of the following hold:

- `counterparty == vendor` (case-insensitive, trimmed)
- `ccy` equal
- `side == action` (one of `BUY`, `SELL`, `SHORT SELL`, `BUY TO COVER`)
- `|gross_amt - amount|` within tolerance — `max(1.00, 1 bp of |gross_amt|)`
- `value_date` equals either `trade_date` **or** `settl_date`

If several book rows qualify for one email row, the one with the smallest absolute amount difference wins. A book row already matched in a run cannot be reused. Every row in the result carries a human-readable `reason` so the caller can explain non-matches.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   MCP Client    │────▶│   MCP Server    │────▶│   PostgreSQL    │
│  (Unique AI)    │     │   (FastMCP)     │     │ reconciliationdb│
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │    Zitadel      │
                        │  (OAuth2/OIDC)  │
                        └─────────────────┘
```

## Database

Two tables in a PostgreSQL database (default name `reconciliationdb`):

### `customer_book_cashflows` (internal book)

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | Primary key |
| `bfx_trade_id` | TEXT UNIQUE | Internal trade id |
| `instrument` | TEXT | Security name |
| `ccy` | CHAR(3) | Currency |
| `account` | TEXT | Account |
| `counterparty` | TEXT | Counterparty name |
| `side` | TEXT | BUY / SELL / SHORT SELL / BUY TO COVER |
| `trade_date` | DATE | Trade date |
| `settl_date` | DATE | Settlement date |
| `gross_amt` | NUMERIC(20,2) | Signed gross amount |

### `counterparty_email_cashflows` (from emails)

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | Primary key |
| `amount` | NUMERIC(20,2) | Signed amount |
| `ccy` | CHAR(3) | Currency |
| `vendor` | TEXT | Counterparty name |
| `action` | TEXT | BUY / SELL / SHORT SELL / BUY TO COVER |
| `value_date` | DATE | Date the email refers to |
| `email_ref` | TEXT | Source email reference |
| `status` | TEXT | MATCHED / UNMATCHED |
| `matched_customer_cf_id` | INT FK | Matched book row (if any) |
| `difference` | NUMERIC(20,2) | Amount difference of the match |
| `match_reason` | TEXT | Why it matched / did not |
| `matched_at` | TIMESTAMP | When matched |

**Setup:** Create the database (e.g. `az postgres flexible-server db create`, `createdb`, or via Docker Compose) and run **`src/mcp_trade_reconciliation/sql/create_table_postgres.sql`** to create the tables and seed demo data. The seed script drops and recreates the two tables, so it is safe to re-run for a clean demo state.

## Authentication

The server uses **Zitadel** OAuth2/OIDC via FastMCP's `OAuthProxy`:

1. Token introspection via `{ZITADEL_URL}/oauth/v2/introspect`
2. OAuth2 proxy for the authorization flow
3. Valid scopes: `email`, `openid`, `profile`

> **Note:** OAuth client registrations are kept **in memory** in this tutorial, so they do not survive a restart (clients re-register automatically on next connect). To persist them across restarts, add a PostgreSQL-backed client store as shown in [`mcp_sql_demo`](../mcp_sql_demo) (`py-key-value-aio[postgresql]` + `client_storage=`).

## Environment variables

Create a `.env` file (and/or set Azure App settings):

```bash
# PostgreSQL
PGHOST=localhost
PGPORT=5432
PGDATABASE=reconciliationdb
PGUSER=postgres
PGPASSWORD=postgres

# Zitadel
ZITADEL_URL=https://id.unique.app
UPSTREAM_CLIENT_ID=your-zitadel-client-id
UPSTREAM_CLIENT_SECRET=your-zitadel-client-secret

# Server
BASE_URL_ENV=https://your-public-url.ngrok-free.app
MCP_PORT=8003
```

## Local setup

### 1. Start PostgreSQL

```bash
docker compose -f docker_compose.yaml up -d
```

### 2. Seed the database

```bash
psql -h localhost -p 5432 -U postgres -d reconciliationdb \
  -f src/mcp_trade_reconciliation/sql/create_table_postgres.sql
```

### 3. Install dependencies

```bash
uv sync
```

### 4. Run the server

```bash
uv run python src/mcp_trade_reconciliation/mcp_trade_reconciliation.py
```

Server listens on `http://0.0.0.0:8003` (override with `MCP_PORT`). The MCP endpoint is `/mcp`.

## Usage examples

Once connected with an MCP client you can ask, for example:

- "Show me the unmatched counterparty cash flows."
- "Reconcile all open email cash flows against the book."
- "Save a Goldman Sachs BUY of 12,948,000 USD for value date 2026-05-23 and try to match it."
- "Reset the demo data." — restores the baseline so you can run the reconciliation from scratch.

### Resetting the demo

`Reset_Demo_Data` re-runs `create_table_postgres.sql` server-side, so it returns the database to a clean, predictable baseline (10 book rows, 6 email rows, all UNMATCHED) between demo runs. This is the same effect as re-running the seed SQL by hand (see *Re-seed / reset the demo data* below), but available as a tool the assistant can call.

## Deploy to Azure

The deployment mirrors `mcp_sql_demo`: a **PostgreSQL Flexible Server** holds the data, and the MCP server runs as a **Linux container Web App** built from this folder's `Dockerfile` via **Azure Container Registry**.

### Prerequisites

1. **Azure subscription and resource group** — defaults to subscription `698f3b43-ccb0-4f97-9e10-2ca89a7782cf`, resource group `rg-lab-demo-001-sql-mcp` (see the [Labs guide](https://unique-ch.atlassian.net/wiki/spaces/DX/pages/1873739786/Labs) for initial setup). Override with the `SUBSCRIPTION` / `RG` env vars.
2. Azure CLI installed and logged in (`az login`).
3. `psql` on PATH (used to seed the tables; `brew install libpq && brew link --force libpq`).
4. A Zitadel **Web Application** with redirect URI `https://trade-reconciliation-mcp.azurewebsites.net/auth/callback`, access token type **JWT**, token endpoint auth **POST** (`client_secret_post`).

### Resources created by `deploy_pg.sh`

| Resource | Default name |
|----------|--------------|
| PostgreSQL Flexible Server | `trade-reconciliation-mcp-db` |
| Database | `reconciliationdb` |
| Container Registry | `tradereconmcpacr` |
| App Service plan | `trade-reconciliation-mcp-plan` |
| Web App | `trade-reconciliation-mcp` |

All names are overridable via env vars (`APP`, `ACR`, `PG_SERVER`, `PG_DB`, `LOCATION`, ...).

### Deploy

```bash
./deploy_pg.sh
```

What it does (idempotent):

1. Sets the subscription.
2. Creates the PostgreSQL Flexible Server **only on first run** (5–15 min); skipped if it already exists.
3. Creates the database `reconciliationdb`.
4. Adds a firewall rule so the Web App and `psql` can connect.
5. **Seeds** the reconciliation tables from `create_table_postgres.sql` (you will be prompted for the PG admin password, or set `PG_ADMIN_PASSWORD`).
6. Creates the ACR and builds the image from this folder.
7. Creates the App Service plan and Web App (or updates the container image if they exist).
8. Sets app settings: `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `MCP_PORT`, `BASE_URL_ENV`, `ZITADEL_URL`, plus `WEBSITES_PORT=8003` and Always On.

### Set the required secrets

After the script, set the Zitadel client credentials (needed for auth):

```bash
az webapp config appsettings set -n trade-reconciliation-mcp -g rg-lab-demo-001-sql-mcp --settings \
  UPSTREAM_CLIENT_ID=<your-zitadel-client-id> \
  UPSTREAM_CLIENT_SECRET=<your-zitadel-client-secret>
```

### Redeploy (code changes only)

If the database already exists and you only changed code:

```bash
az acr build -t trade-reconciliation-mcp:latest -r tradereconmcpacr .
az webapp config container set -n trade-reconciliation-mcp -g rg-lab-demo-001-sql-mcp \
  --container-image-name "tradereconmcpacr.azurecr.io/trade-reconciliation-mcp:latest"
az webapp restart -n trade-reconciliation-mcp -g rg-lab-demo-001-sql-mcp
```

### Deployed instance

- **App:** `https://trade-reconciliation-mcp.azurewebsites.net`
- **MCP endpoint:** `https://trade-reconciliation-mcp.azurewebsites.net/mcp`

### Re-seed / reset the demo data

The seed script is destructive (drops + recreates the tables), so re-running it resets the demo:

```bash
PG_FQDN=$(az postgres flexible-server show -n trade-reconciliation-mcp-db -g rg-lab-demo-001-sql-mcp --query fullyQualifiedDomainName -o tsv)
PGPASSWORD=<admin-password> psql "postgresql://pgadmin@${PG_FQDN}:5432/reconciliationdb?sslmode=require" \
  -f src/mcp_trade_reconciliation/sql/create_table_postgres.sql
```

## Dependencies

- `fastmcp` – MCP server framework (incl. OAuth proxy)
- `fastapi` – web framework / responses
- `pydantic` – data validation
- `psycopg2-binary` – PostgreSQL driver
- `python-dotenv` – `.env` loading
