# RM Agent — CRM MCP

The **CRM** server is the relationship side of the RM Agent — who we serve and the
context around them. Built the same way as [`mcp_sql_demo`](../../mcp_sql_demo) /
[`mcp_advisory`](../mcp_advisory): a standalone **FastMCP** HTTP server backed by
**PostgreSQL**, deployed to an Azure Web App. It **shares the same database** as
the Advisory server (`rmmcps`).

| Domain | Tools |
|---|---|
| `crm` | `get_party_identity`, `get_identifiers`, `get_entity_ownership`, `get_relationship`, `get_mandate_objectives`, `get_history`, `list_clients`, `list_available_documents` |
| `client_memory` (stateful) | `get_talking_points` / `upsert_talking_point` / `delete_talking_point`; `get_open_questions` / `upsert_open_question` / `delete_open_question`; `list_documents` / `upsert_document` / `delete_document` |
| `calendar` | `get_meetings`, `get_next_meeting` |
| _(server)_ | `Reset_Demo_Data` — restore all tables to the seed baseline (DESTRUCTIVE; restores edited client memory). For demos. |

As with Advisory, data that lived inline in the n8n JS / Data Tables now lives in
**Postgres tables** seeded from `sql/*.sql` and read with psycopg2. Client memory
is the only **editable** part (real INSERT/UPDATE/DELETE); everything else is
read-only. One id everywhere: **`client_id`** (names + legacy numeric ids still
resolve via `client_aliases`).

## Layout

```
src/mcp_crm/
  mcp_crm.py             # FastMCP server (HTTP /mcp, port 8004), registers domains
  common/db.py           # shared psycopg2 access + client resolution + tool factory
  crm.py                 # identity/relationship/etc. + list_clients + list_available_documents
  client_memory.py       # editable talking points / open questions / documents
  meetings.py            # calendar (named `meetings` so it never shadows stdlib `calendar`)
  sql/                   # clients.sql, crm.sql, client_memory.sql, calendar.sql (generated)
```

The SQL is generated from the canonical registry by
`python/rm-demo/src/generate_sql.py` in the sandbox repo (do not edit by hand).

## Run locally

The CRM and Advisory servers share one database. Run **one** Postgres and seed
both packages' SQL into it:

```bash
cd tutorials/mcp/rm_mcps/mcp_crm
docker compose -f docker_compose.yaml up -d        # postgres on :5432, db mcpdb
for f in src/mcp_crm/sql/*.sql ../mcp_advisory/src/mcp_advisory/sql/*.sql; do
  psql -h localhost -p 5432 -U postgres -d mcpdb -f "$f"   # password: postgres
done
uv sync
uv run python src/mcp_crm/mcp_crm.py
```

MCP endpoint: `http://127.0.0.1:8004/mcp`. Health: `curl http://127.0.0.1:8004/`.

## Tests

```bash
uv sync                          # installs pytest (dev group)
uv run pytest tests/unit         # env-agnostic unit tests — no DB needed
uv run pytest -m integration     # integration — needs seeded Postgres (+ running server for the http tests)
```

`tests/unit/` monkeypatch the DB layer, so they run anywhere (verified with a
bogus `PGHOST`); they include the client-memory write logic (upsert/delete/
truncation). `tests/integration/` assert real results against the seeded
database and the live `…/mcp` endpoint (incl. a client-memory CRUD round-trip and
a `Reset_Demo_Data` baseline check), and **skip themselves** when the DB / server
isn't up.

## Deploy to Azure

### Prerequisites

1. **Azure subscription and resource group** — subscription `698f3b43-ccb0-4f97-9e10-2ca89a7782cf` (`lab-demo-001`), resource group `rg-lab-demo-001-rm-agent-mcp`. The lab uses one pre-created RG per MCP and personal accounts can't create RGs at subscription scope, so have this RG created first (see the [Labs guide](https://unique-ch.atlassian.net/wiki/spaces/DX/pages/1873739786/Labs)), or set `RG=` to an existing lab RG you have Contributor on.
2. **Advisory deployed first** — CRM reuses the shared ACR (`rmmcpsacr`) and Postgres server (`rm-mcps-pg-db`) created by `mcp_advisory/deploy_pg.sh`. Use the **same** `PG_ADMIN_PASSWORD`.
3. **Azure CLI** installed and logged in (`az login`) with access to the subscription above.
4. **`psql`** on PATH — `deploy_pg.sh` seeds the database with it (e.g. `brew install libpq && brew link --force libpq`).
5. *(Optional)* **Zitadel app** with redirect URI `https://rm-crm-mcp.azurewebsites.net/auth/callback` — only needed if you enable OAuth (the server runs open without it).

### Deploy

Deploy **Advisory first** (it creates the shared ACR + Postgres server), then:

```bash
./deploy_pg.sh        # uses the same PG_ADMIN_PASSWORD as the shared rm-mcps-pg-db
```

- **App:** `https://rm-crm-mcp.azurewebsites.net`  ·  **MCP endpoint:** `…/mcp`
- Rewire the **`RM Agent - CRM`** Unique connector to the new endpoint. Because this is
  one shared deployment across environments, put the env in the URL **path** so the
  server returns that environment's KB content ids: `…/<env>/mcp` (e.g. `…/sales/mcp`,
  `…/uat/mcp`; plain `…/mcp` ⇒ the `RM_DEFAULT_ENV`, `qa`). See
  [Environment-aware content ids](../README.md#environment-aware-content-ids).

### Redeploy (code / seed changes)

The web app is **pinned to a timestamp tag**, so building `:latest` + restarting does
**nothing**. Use the shared script — it builds a fresh timestamp tag, repoints the app
(`az webapp config container set`), and restarts (RG `rg-lab-demo-001-rm-agent-mcp`,
needs Web App Contributor):

```bash
../.local/redeploy.sh crm
```

Seed SQL is baked into the image, so **run `Reset_Demo_Data` after redeploying** to apply
new/changed seed data — e.g. a refreshed `content_id_map` (the env-specific KB content ids;
see the [top-level README](../README.md#environment-aware-content-ids)).
