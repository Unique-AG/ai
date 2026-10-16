# RM Agent — Advisory MCP

The **Advisory** server is the investment/portfolio side of the RM Agent — the
market intelligence and portfolio data the RM uses to advise. It is built the
same way as [`mcp_sql_demo`](../../mcp_sql_demo): a standalone **FastMCP** HTTP
server backed by **PostgreSQL** and deployed to an Azure Web App. The
relationship side (CRM, client memory, calendar) is a separate server,
`mcp_crm`.

Each domain lives in its own subpackage and is wired in with one
`register(mcp)` call, so the remaining domains drop in as one-liners.

| Domain | Tools |
|---|---|
| `house_views` | `get_house_view`, `get_cio_themes`, `get_tactical_calls` |
| `portfolios` | `get_holdings`, `get_performance`, `get_portfolio_transactions`, `get_attribution`, `get_risk_exposure` |
| `transactions` | `get_corporate_actions`, `get_elections`, `get_orders`, `get_tax_lots`, `get_transaction_monitoring` |
| `model_portfolios` | `list_model_portfolios`, `get_model_portfolio`, `recommend_model` |
| `lombard` | `get_coverage_scenario` |

17 tools, plus **`Reset_Demo_Data`** (restore this server's tables to the seed
baseline — DESTRUCTIVE; for demos) = 18. Each per-client tool accepts `input`
(client name or client_id); names and legacy numeric ids resolve via the shared
`client_aliases` table.

The difference from n8n: data that used to live inline in JavaScript
(`toolCode` nodes) now lives in **Postgres tables** seeded from `sql/*.sql` (one
file per domain) and read with psycopg2 — no workflow engine, no
persistent-trigger heap (the thing that kept OOM-ing on n8n).

## House Views tools

Same three tool names, descriptions and output shape as the n8n workflow:

| Tool | Source table | Input | Returns |
|---|---|---|---|
| `get_house_view` | `house_view` (+ `house_view_meta`) | `all` / `current` for the full view, or an asset class (`equities`, `fixed income`, `alternatives`, `fx`, `cash`) | `{house, as_of, valid_until, views[]}` — or a single class, or `{error, available[]}` |
| `get_cio_themes` | `cio_themes` | `all` (or omit) | `{house, as_of, count, themes[]}` |
| `get_tactical_calls` | `tactical_calls` | `all` (or omit) | `{house, as_of, count, calls[]}` |

All House Views data is **bank-wide** (not per client). `get_house_view`
understands the same synonyms as the n8n version (`bonds`→fixed income,
`equity`→equities, `alts`→alternatives).

## Layout

```
src/mcp_advisory/
  mcp_advisory.py        # FastMCP server (HTTP /mcp), build_auth, status/favicon, registers domains
  common/db.py           # shared psycopg2 access + client resolution + tool factory + reset
  house_views.py         # bank-wide CIO data (custom tables; uses common.db)
  portfolios.py          # spec-driven per-client tools (holdings/performance/…)
  transactions.py        # spec-driven per-client tools (corporate actions/…)
  model_portfolios.py    # catalogue (list/get) + per-client recommendation
  lombard.py             # facility coverage scenarios
  sql/                   # clients.sql + one <domain>.sql per domain (generated)
```

Per-client read-only data is stored as `<table>(client_id TEXT PK, data JSONB)` and
read by a small factory in `common/db.py`; most domains are therefore just a
declarative `SPECS` list + `register(mcp)`. The SQL is generated from the
canonical registry by `python/rm-demo/src/generate_sql.py` in the sandbox repo.

Adding a domain = a new module exposing `register(mcp)`, a `sql/<domain>.sql`, and
one import line in `mcp_advisory.py`.

## Run locally

```bash
cd tutorials/mcp/rm_mcps/mcp_advisory

# 1) Postgres
docker compose -f docker_compose.yaml up -d
for f in src/mcp_advisory/sql/*.sql; do
  psql -h localhost -p 5432 -U postgres -d mcpdb -f "$f"   # password: postgres
done

# 2) deps + run
uv sync
uv run python src/mcp_advisory/mcp_advisory.py
```

Server listens on `http://127.0.0.1:8003`; MCP endpoint at `http://127.0.0.1:8003/mcp`.
Health check: `curl http://127.0.0.1:8003/` → `{"server":"running","name":"RM Agent - Advisory"}`.

## Environment variables

```bash
# PostgreSQL (defaults shown — match docker_compose.yaml)
PGHOST=localhost
PGPORT=5432
PGDATABASE=mcpdb
PGUSER=postgres
PGPASSWORD=postgres
PORT=8003

# Optional OAuth (Zitadel) — when UNSET, the server runs open (fine for this
# bank-wide, read-only data). Set all three to enable auth like mcp_sql_demo:
# ZITADEL_URL=https://id.unique.app
# UPSTREAM_CLIENT_ID=...
# UPSTREAM_CLIENT_SECRET=...
# PG_CLIENT_STORAGE_URL=postgresql://user:pass@host:5432/db   # OAuth client persistence
```

## Tests

```bash
uv sync                          # installs pytest (dev group)
uv run pytest tests/unit         # env-agnostic unit tests — no DB needed
uv run pytest -m integration     # integration — needs seeded Postgres (+ running server for the http tests)
```

`tests/unit/` monkeypatch the DB layer, so they run anywhere (verified with a
bogus `PGHOST`). `tests/integration/` assert real results against the seeded
database and the live `…/mcp` endpoint, and **skip themselves** when the DB /
server isn't up.

## Deploy to Azure

### Prerequisites

1. **Azure subscription and resource group** — subscription `698f3b43-ccb0-4f97-9e10-2ca89a7782cf` (`lab-demo-001`), resource group `rg-lab-demo-001-rm-agent-mcp`. The lab uses one pre-created RG per MCP and personal accounts can't create RGs at subscription scope, so have this RG created first (see the [Labs guide](https://unique-ch.atlassian.net/wiki/spaces/DX/pages/1873739786/Labs)), or set `RG=` to an existing lab RG you have Contributor on.
2. **Azure CLI** installed and logged in (`az login`) with access to the subscription above.
3. **`psql`** on PATH — `deploy_pg.sh` seeds the database with it (e.g. `brew install libpq && brew link --force libpq`).
4. *(Optional)* **Zitadel app** with redirect URI `https://rm-advisory-mcp.azurewebsites.net/auth/callback` — only needed if you enable OAuth (the server runs open without it).

### Deploy

```bash
./deploy_pg.sh        # prompts for PG_ADMIN_PASSWORD on first run
```

Creates (idempotently) a shared `rmmcpsacr` registry + `rm-mcps-pg-db` Postgres
server in resource group `rg-lab-demo-001-rm-agent-mcp`, seeds every `sql/*.sql`, and
deploys the Web App `rm-advisory-mcp`. On later runs only the image is rebuilt
and redeployed.

- **App:** `https://rm-advisory-mcp.azurewebsites.net`
- **MCP endpoint:** `https://rm-advisory-mcp.azurewebsites.net/mcp`

### Rewire the Unique connector

Point the **`RM Agent - Advisory`** connector at the new endpoint:

```
RM Agent - Advisory → https://rm-advisory-mcp.azurewebsites.net/mcp
```

Advisory data is **env-invariant** (no KB content ids), so a plain `…/mcp` is correct
for every environment. For a uniform convention with the CRM connector it *also* accepts
the env-in-path form `…/<env>/mcp` (e.g. `…/sales/mcp`): the env segment is stripped and
ignored (`EnvPathMiddleware`), so both connectors can follow the identical rule.

Tool names, descriptions and output are unchanged, so the agent behaves exactly
as it did against n8n — just against a service that doesn't fall over.

### Redeploy (code / seed changes)

The web app is **pinned to a timestamp tag**, so building `:latest` + restarting does
**nothing**. Use the shared script — it builds a fresh timestamp tag, repoints the app,
and restarts (RG `rg-lab-demo-001-rm-agent-mcp`, needs Web App Contributor):

```bash
../.local/redeploy.sh advisory
```

Seed SQL is baked into the image, so **run `Reset_Demo_Data` after redeploying** to apply
new/changed seed data.
