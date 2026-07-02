# RM Agent MCPs

Migration of the **RM Agent** wealth-management demo from n8n MCP workflows to
real, deployable MCP servers — built the same way as
[`mcp_sql_demo`](../mcp_sql_demo) (standalone **FastMCP** servers backed by
**PostgreSQL**, deployed to Azure Web Apps).

**Why:** the n8n MCP layer kept running out of memory — persistent SSE triggers
plus data held inline in JavaScript. These servers are stateless, store their
data in Postgres, and restart cleanly.

> **See [ARCHITECTURE.md](ARCHITECTURE.md)** for the full design — storage model,
> client resolution, the tool factory, the data pipeline, reset, auth, and how to
> extend.

The nine n8n workflows consolidate into **two** servers, split by what the data
*is*:

| Server | Package | Domains (tools) | App | Endpoint |
|---|---|---|---|---|
| **Advisory** — investment/portfolio side | [`mcp_advisory`](mcp_advisory) | house views, client portfolios, transactions, model portfolios, lombard coverage (**17 tools + reset**) | `rm-advisory-mcp` | `:8003/mcp` |
| **CRM** — relationship side | [`mcp_crm`](mcp_crm) | CRM, client memory, calendar (**19 tools + reset**) | `rm-crm-mcp` | `:8004/mcp` |

Each server also exposes **`Reset_Demo_Data`** (like `mcp_trade_reconciliation`) —
a DESTRUCTIVE tool that truncates that server's tables and re-runs its `sql/*.sql`
seeds, restoring the baseline (notably the editable CRM client memory) between demo
runs.

Both servers share **one** PostgreSQL database (`rmmcps`), one ACR (`rmmcpsacr`),
and one resource group (`rg-lab-demo-001-rm-mcps`). One id everywhere:
**`client_id`** (textual; names + legacy numeric ids resolve via `client_aliases`).
OAuth (Zitadel) is wired like `mcp_sql_demo` but optional (open when unset).

## Storage

Data that lived inline in the n8n JS / Data Tables now lives in Postgres,
generated from the canonical registry:

- **Read-only per-client records** → `<table>(client_id TEXT PK, data JSONB)`,
  returned spread as `{client_id, …}` (object) or `{client_id, <field>:[…], count}` (array).
- **Roster + resolution** → `clients`, `client_aliases`.
- **Editable client memory** → `rm_talking_points` / `rm_open_questions` / `rm_documents` rows.
- **Calendar / model catalogue / lombard** → `calendar_events`, `model_catalog` + `model_portfolios`, `lombard_coverage`.

The seed SQL is **generated** (do not hand-edit) by, in the sandbox repo:

```bash
node   python/rm_mcps_export/harvest_n8n.js     # data that lived only in n8n JS
uv run python python/rm_mcps_export/generate_sql.py   # → both packages' sql/*.sql
```

## Run both locally

They share one database — run **one** Postgres and seed both packages' SQL:

```bash
cd tutorials/mcp/rm_mcps/mcp_advisory
docker compose -f docker_compose.yaml up -d                 # postgres on :5432, db mcpdb
for f in ../mcp_advisory/src/mcp_advisory/sql/*.sql ../mcp_crm/src/mcp_crm/sql/*.sql; do
  psql -h localhost -p 5432 -U postgres -d mcpdb -f "$f"    # password: postgres
done
( cd ../mcp_advisory && uv sync && uv run python src/mcp_advisory/mcp_advisory.py )   # :8003
( cd ../mcp_crm      && uv sync && uv run python src/mcp_crm/mcp_crm.py )             # :8004
```

## Tests

Each package has env-agnostic **unit** tests (monkeypatched DB — no Postgres) and
separate **integration** tests (real seeded DB + live `…/mcp` endpoint, which skip
when unavailable):

```bash
cd mcp_advisory   # or mcp_crm
uv run pytest tests/unit       # no DB needed
uv run pytest -m integration   # needs docker compose up + seeds (+ running server)
```

## Deploy to Azure

Deploy **Advisory first** (it creates the shared ACR + Postgres server), then CRM:

```bash
( cd mcp_advisory && ./deploy_pg.sh )   # prompts for PG_ADMIN_PASSWORD on first run
( cd mcp_crm      && ./deploy_pg.sh )   # reuse the SAME PG_ADMIN_PASSWORD
```

Then rewire the two Unique connectors (`RM Agent - Advisory`, `RM Agent - CRM`) to
the new endpoints. See each package's README for details.
