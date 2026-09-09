# RM MCP servers — handoff notes

Everything needed to operate the RM Agent MCP demo. Committed (sanitized)
2026-07-29 on the `florian/mcps-handover` branch: scripts live in `ops/`,
secret values do NOT live in git — each `ops/*.example` file documents the
shape and says where the real value is (Azure app settings / Zitadel console /
1Password).

## What this is

Two FastMCP HTTP servers under `tutorials/mcp/rm_mcps/` replacing 9 n8n MCP
workflows for the RM Agent demo:

- **mcp_advisory** (port 8003) — 18 read-only advisory tools (positions, proposals,
  suitability, transactions, research …).
- **mcp_crm** (port 8004) — 22 tools: CRM reads, calendar, editable client memory
  (talking points / open questions / documents), `edit_dashboard_section`,
  `screen_person` (WorldCheck port — deployed 2026-07-02, but the `worldcheck`
  table only exists after a demo-data reset), and `Reset_Demo_Data`.

Both share one Postgres DB. Client names/legacy ids resolve via the
`client_aliases` table. Full tool reference: `../MCP_SERVERS.md`.

- **Branch:** `feat/rm-mcps-tutorial` — PR https://github.com/Unique-AG/ai/pull/1951
- **Infra PR:** https://github.com/Unique-AG/infrastructure/pull/3103 (lab RG,
  owner group Team Data-Flow `838f7d2d-2b16-4d25-ba91-7dd9d399aff7`)
- **JIRA:** UN-22385 (Azure lab RG + Contributor access, assigned to Dominik)

## Repo layout (changed 2026-07-02 — do not trust older notes)

- `/Users/florian/repos/ai` — back on `main`; has NO rm_mcps source.
- `/Users/florian/repos/ai-rm-mcps` — dedicated checkout of `feat/rm-mcps-tutorial`
  (currently `372aeb6f`, clean). **All rm_mcps work happens here.**

Latest branch commits: `372aeb6f` (client-memory delete returns real rowcount),
`ce3725d0` (screen_person + `sql/worldcheck.sql`, 177 records),
`f8680b0c` (merge main; only conflict was `uv.lock`, took main's).

## Deployed Azure resources

| Thing | Value |
|---|---|
| Subscription | `698f3b43-ccb0-4f97-9e10-2ca89a7782cf` |
| Resource group | `rg-lab-demo-001-rm-agent-mcp` (resources in westeurope) |
| Postgres | `rm-agent-mcp-pgdb` (Flexible Server B1ms), DB `rmmcps`, firewall rule `AllowAll` |
| ACR | `rmmcpsacr` |
| Web apps | `rm-advisory-mcp`, `rm-crm-mcp` → `https://rm-{advisory,crm}-mcp.azurewebsites.net/mcp` |
| Trade rec | `rm-trade-rec-mcp` (deployed 2026-07-10) → `https://rm-trade-rec-mcp.azurewebsites.net/mcp` |

**Trade Reconciliation MCP** (source: `tutorials/mcp/mcp_trade_reconciliation`, NOT
under rm_mcps): 6 tools (cashflow reads, Match_Cashflows, Derive_Break_Actions,
Save_Counterparty_Email_Cashflow, Reset_Demo_Data). Differences vs the other two:
- **Zitadel OAuth built in** (FastMCP OAuthProxy). `UPSTREAM_CLIENT_ID` /
  `UPSTREAM_CLIENT_SECRET` set 2026-07-10 from the Zitadel Web app
  `rm-trade-rec-mcp` (Cluster IAM / Unique Apps project; auth method Basic;
  redirect URI `https://rm-trade-rec-mcp.azurewebsites.net/auth/callback`).
  Credentials: Zitadel console or the web app's app settings; shape in
  `ops/zitadel-trade-rec.txt.example`. **The Zitadel app lives on the
  QA instance** → `ZITADEL_URL=https://id.qa.unique.app` (prod id.unique.app
  returned Errors.App.NotFound). The connector is used from the QA platform
  (next.qa.unique.app); for prod, create a prod Zitadel app and flip
  ZITADEL_URL + UPSTREAM_* accordingly.
- **FastMCP token-endpoint gotcha (root cause of QA connect failures):**
  FastMCP (3.4.2 AND 3.4.4) only parses client credentials from the POST body
  at /token, yet advertises client_secret_basic in its metadata; the MCP TS SDK
  (1.29.0, `selectClientAuthMethod`) prefers basic when advertised → every
  token exchange 401'd ("Missing client_id"). Fixed with the
  `AdvertisePostAuthOnly` middleware in `mcp_trade_reconciliation.py`
  (rewrites /.well-known metadata to advertise client_secret_post only).
  Also upgraded to fastmcp 3.4.4 and relaxed uv `exclude-newer` to "1 day".
  Worth reporting upstream to FastMCP. The middleware is also ported to both
  RM servers as `common/oauth_metadata.py` (commit 68a79a08) — inert until
  OAuth is enabled on their deployments. Diagnose with:
  `curl -X POST .../token -u id:secret ...` (basic) vs `-d client_id=...` (post).
- **Zitadel QA project gate:** users connecting must have an Authorization
  (any role) on the Cluster IAM "Unique Apps" project — it has "Check
  authorization on Authentication" + "Check for Project on Authentication"
  enabled (shared with Factset MCP / MCP Hub; do NOT disable). Florian's user
  was added 2026-07-10.
- **CONNECTED on QA 2026-07-10** ✅ via plain DCR (Add Connector with
  Advanced Options EMPTY — do NOT enter pre-registered creds; that path
  errors "Unauthorized"). Working chain: DCR /register → consent →
  id.qa.unique.app login (user needs an Authorization on the Unique Apps
  project) → /auth/callback → /token (client_secret_post) → connected.
  Note: node-chat caches a pending authorize URL for 5 min (TTL refreshed on
  every Connect click) — after changing anything server-side, wait >5 min or
  the old URL keeps being served.
- **Platform-side stale-client gotcha:** node-chat stores its DCR client info
  keyed by URL+company; if the server loses the registration, the platform
  loops on "Client Not Registered" (delete/re-add does NOT clear it). Fixes:
  paste pre-registered credentials in the Authenticate modal
  (shape in `ops/trade-rec-preregistered-client.txt.example`; the real pair is
  persisted in reconciliationdb's kv_store, registered
  via the server's open /register endpoint with next.unique.app chat/admin
  callback URIs; FastMCP accepts other callbacks too, with a consent warning,
  since allowed_client_redirect_uris=None) or run the
  `mcpOauthClientInformationDelete(url)` GraphQL mutation (chat.admin.all, no UI).
- **OAuth client registrations persisted in Postgres** since tag
  `20260710151429`: `client_storage=PostgreSQLStore` wired into the OAuthProxy
  (uncommitted local edit to `mcp_trade_reconciliation.py` + `pyproject.toml`,
  pattern copied from `mcp_sql_demo`), app setting `PG_CLIENT_STORAGE_URL`
  → `reconciliationdb?sslmode=require`. Before this, registrations were
  in-memory and every restart produced "Client Not Registered" for
  already-connected clients.
- **Own database `reconciliationdb`** on the shared `rm-agent-mcp-pgdb` server,
  seeded directly via psql (NOT baked into the image — reseed with:
  `psql .../reconciliationdb?sslmode=require -f src/mcp_trade_reconciliation/sql/create_table_postgres.sql`);
  its Reset_Demo_Data tool reseeds from the SQL bundled in the image.
- Image `rm-trade-rec-mcp:20260710120000` in `rmmcpsacr`; plan `rm-trade-rec-mcp-plan` (B1).

PG credentials: shape in `ops/azure-pg-connection.txt.example`; the real password
is in the web apps' app settings / 1Password. **Never inline the password in a
command** (it leaks into shell history).

## ⚠️ IN-FLIGHT TASK — redeploy DONE (2026-07-02), demo-data reset PENDING

Goal: make `screen_person` + `worldcheck` seed live on `rm-crm-mcp`.

Done (2026-07-02, via `./redeploy.sh both`):
1. Both apps rebuilt at tag `20260702104433` (ACR runs dt15 advisory / dt16 crm),
   repointed via `az webapp config container set`, restarted.
2. Verified live with `mcp_call.py list`: advisory = 18 tools, crm = **22 tools
   including `screen_person`**. The pinned-timestamp-tag gotcha (below in
   Scripts) is what had blocked the earlier `:latest`-only attempt (Run dt14).

DONE 2026-07-03: the `worldcheck` table is live and seeded (reset happened) —
smoke test `mcp_call.py … call screen_person '{"name":"Yelena Volkova"}'`
returned records_screened=177 and an exact match (WC-1004572). Note the
required param is `name` (not `full_name`); it is the only required field.

## Scripts (`ops/`)

- **`redeploy.sh [advisory|crm|both]`** — az acr build (timestamp tag + latest)
  → `az webapp config container set` → restart. Fixed 2026-07-02 for the
  pinned-tag gotcha; ran successfully 2026-07-02 (`both`, tag `20260702104433`).
- **`mcp_call.py <url> list | call <tool> '<json>'`** — minimal MCP
  streamable-HTTP client (handshake + tools/list + tools/call) for smoke tests.
- **`azure-pg-connection.txt.example`** — PG connection shape (real password in
  app settings / 1Password).

## Critical workflows & gotchas

- **Demo-data change:** SQL seeds are baked into the image. Order is always:
  edit `sql/*.sql` → `redeploy.sh` → **then** Reset_Demo_Data. Reset before
  redeploy restores the OLD data.
- **az CLI flag drift (az 2.87):** PG `db create` uses `-n` (not `--database-name`);
  firewall rules use `--server-name` + `--name`. Never mask failures with `|| echo`.
- **Chain deploy steps with `&&`**, not newlines — otherwise later steps run
  after earlier ones fail.
- Web apps read DB config from app-settings env; if they hit `localhost:5432`,
  they started with stale env → restart them.

## Open items

- **Bugbot thread 3481391134** on PR #1951, unresolved: `get_next_meeting`
  (`mcp_crm/src/mcp_crm/meetings.py`) can return past events. Awaiting user
  decision: fixed demo anchor date (2026-06-23, recommended) vs real current
  date. All other Bugbot threads are fixed/replied/resolved.
- **João needs psql access** — share credentials via 1Password (never inline in
  Slack); optionally create him a dedicated read-only PG role instead of admin.
- Pre-existing E501 in `mcp_crm/src/mcp_crm/client_memory.py` (~line 115,
  `list_documents`) — not ours, left alone.

## Review-loop conventions (PR #1951)

Bugbot comments: fix when sensible, otherwise reply-decline with rationale.
Reply on each thread via `gh api …/replies`, end every reply with
`_🤖 Addressed by [Claude Code](https://claude.com/claude-code)_`, then resolve
the thread via GraphQL `resolveReviewThread`. Don't reply on threads not yet
addressed. Conventional commits; commit trailer
`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
