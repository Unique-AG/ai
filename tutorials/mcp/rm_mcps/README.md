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
and one resource group (`rg-lab-demo-001-rm-agent-mcp`). One id everywhere:
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
- **Env-specific KB content ids** → `content_id_map(env, map_key, content_id)` — see [Environment-aware content ids](#environment-aware-content-ids).

The seed SQL is **generated** (do not hand-edit) by, in the sandbox repo (single
source of truth = `client_registry.py`):

```bash
uv run --project python/rm-demo python python/rm-demo/src/generate_sql.py   # → both packages' sql/*.sql
```

## Environment-aware content ids

These MCPs are a **single shared deployment** used by every environment (QA / UAT /
prod-bnpp / prod-sales / local). KB **content ids (`cont_…`) are env-specific** — the
same document has a different id in each environment's Knowledge Base — so the CRM
tools must return the id for the **caller's** environment, not a baked-in one.

- **Env signal — `env_map.env_from_ctx`, in priority order:** (1) the **env as a URL
  path segment** on the connector — `https://rm-crm-mcp.azurewebsites.net/<env>/mcp`
  (e.g. `…/sales/mcp`), set per environment in admin. This is the primary signal: it
  needs **no** platform feature, and unlike a `?env=` query (which the prod admin
  rejects as an "Invalid MCP server url") a plain path is accepted. A tiny ASGI
  middleware (`mcp_crm.EnvPathMiddleware`) peels the known-env segment off the path,
  records it for the request, and rewrites the path back to `/mcp` so FastMCP routes
  normally — robust to `/<env>/mcp` and `/mcp/<env>`. (2) a `?env=<env>` **query**
  (same effect, but only usable for direct/local testing since prod admin rejects it);
  (3) the forwarded **`_meta.companyId`** (mapped by `COMPANY_ENV`) *if* the connector
  has the `unique.app/auth/` forwarding namespace enabled; (4) else `RM_DEFAULT_ENV`
  (default `qa`). Only the CRM connector *needs* an env, but **both** servers accept the
  same `…/<env>/mcp` URL shape: Advisory has no content ids, so it strips and **ignores**
  the env segment — that way both connectors follow one rule and an env-prefixed Advisory
  URL never 404s.
- `mcp_crm/common/env_map.py` maps `companyId → env` (`COMPANY_ENV`; override at
  deploy time with `RM_COMPANY_ENV_JSON`, default env via `RM_DEFAULT_ENV`) and looks
  the id up in `content_id_map(env, map_key, content_id)` — keys `dashboard:<client_id>`,
  `cockpit`, `doc:<client_id>:<filename>`.
- `list_clients` (dashboard `content_id` / `open_doc_payload`) and
  `list_available_documents` (each doc's `contentId`) resolve per env.
- **Graceful degradation:** unknown company / forwarding off / unseeded `(env, key)` →
  the tool returns `content_id = ""`, so consumers open by **`filePath`** (which is
  env-agnostic) instead of a wrong/dead id. A missing map never breaks a link.

`content_id_map` is seeded from `resources/rm-demo/{dashboard,document}_content_ids.<env>.json`
in the sandbox repo (per env, refreshed by `fetch_*_ids.py --env user.<env>.env` after
uploads). Envs without a map file simply fall back to `filePath`.

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

**To redeploy code / seed changes** (after the initial deploy) use
[`.local/redeploy.sh`](.local/redeploy.sh) `[advisory|crm|both]` — it builds a fresh
**timestamp-tagged** image (the web apps are pinned to timestamp tags, so `:latest` +
restart is a no-op), repoints the web app, and restarts. Everything lives in RG
**`rg-lab-demo-001-rm-agent-mcp`** (needs Web App Contributor). Seed SQL is baked into
the image, so **run `Reset_Demo_Data` after redeploying** to apply new/changed seed
data (e.g. a refreshed `content_id_map`).
