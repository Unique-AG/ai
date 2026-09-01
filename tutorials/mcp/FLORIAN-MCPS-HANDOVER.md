# Florian's MCPs — handover map (2026-07-29)

Branch `florian/mcps-handover` holds all of Florian's MCP work, split in two
groups (plus one standalone demo). Secrets are NEVER in git — every credential
lives in Azure app settings, the Zitadel console, or 1Password; `*.example`
files document the shapes.

## 1. Equity analyst demo MCP — `mcp_equity_analyst/`

The "CIB - Sell-Side Equity Analyst" demo (Exane BNPP sell-side research):
29 tools — synthetic coverage universe (6 luxury names), live Yahoo quotes with
sparklines + detailed 2y weekly charts, scenario engine, editable house views
(thesis / scenarios / desk notes / morning brief), Excel model builder,
maker/checker control queue, per-env jobs engine and a 00:00/08:00 Zurich
nightly that regenerates 19 documents per environment into the Unique KB via
the Unique SDK.

- Deployed: web app `fa-research-mcp` (rg-lab-demo-001-sql-mcp, ACR
  `tradereconmcpacr`) → `https://fa-research-mcp.azurewebsites.net/<env>/mcp`
  and `/…/<env>/admin` (env = qa | uat | sales | bnpp | local).
- App settings (names only): `FA_SDK_CREDS_JSON` (per-env Unique SDK creds),
  `FA_REVIEW_IDS_BY_ENV_JSON`, `FA_NOTE_IDS_BY_ENV_JSON`, `FA_AUTO_REBASE`.
- Platform: spaces + KB folder "CIB - Sell-Side Equity Analyst" in qa/uat/sales;
  connector name "Demo - CIB - Sell-Side Equity Analyst" (must match exactly).
- Companion assets (canvases, skills, builders, content-id sidecars) live in
  the monorepo under `python/research/demo_lab/` (PR Unique-AG/monorepo#27496):
  `python/equity-analyst-demo/`, `resources/tools/kb/CIB - Sell-Side Equity
  Analyst/` and `resources/equity-analyst-demo/`.
- Folder renamed from `mcp_fa_research` on this branch (inner Python package
  and the deployed web app keep the old name).

## 2. RM MCPs — `rm_mcps/`

Two FastMCP HTTP servers replacing 9 n8n MCP workflows for the RM Agent demo,
sharing one Postgres (`rm-agent-mcp-pgdb`, DB `rmmcps`):

- `mcp_advisory` — 18 read-only advisory tools (positions, proposals,
  suitability, transactions, research…). Web app `rm-advisory-mcp`.
- `mcp_crm` — 22 tools: CRM reads, calendar, editable client memory,
  `edit_dashboard_section`, `screen_person` (WorldCheck), `Reset_Demo_Data`.
  Web app `rm-crm-mcp`.

Operating guide: `rm_mcps/HANDOFF.md` (gotchas, deploy order, OAuth notes).
Scripts: `rm_mcps/ops/` (redeploy.sh, mcp_call.py, credential shapes).
Tool reference: `rm_mcps/MCP_SERVERS.md` · Architecture: `rm_mcps/ARCHITECTURE.md`.

## 3. Trade reconciliation MCP — `mcp_trade_reconciliation/` (standalone)

6 tools (cashflow reads/match/break actions), own DB `reconciliationdb` on the
shared PG server, Zitadel OAuth built in (QA instance), web app
`rm-trade-rec-mcp`. The OAuth/DCR war stories are in `rm_mcps/HANDOFF.md` —
read them before touching auth.

## Cross-cutting gotchas

- Web apps are pinned to TIMESTAMP image tags, never `:latest` — always
  `az acr build` a fresh tag, `az webapp config container set`, restart.
- After a deploy the OLD container can answer for 2–4 min — probe a marker
  only the new code has, never just "the endpoint answers".
- SQL seeds are baked into images: edit SQL → redeploy → THEN Reset_Demo_Data.
- Connector tool registries are snapshots: after adding tools/params, re-sync
  the connector in admin ("Refresh Tool Settings") in every environment.
