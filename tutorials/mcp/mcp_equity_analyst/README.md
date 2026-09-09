# Equity Analyst MCP (formerly fa-demo / FA Research)

> Folder renamed from `mcp_fa_research` on the handover branch — the inner
> Python package (`src/mcp_fa_research`), the deployed web app
> (`fa-research-mcp`) and its image name are unchanged. The server has grown to
> **29 tools** (live quotes + charts, scenario engine, editable house views,
> jobs engine, nightly SDK regeneration, Excel models, maker/checker) — see
> `../FLORIAN-MCPS-HANDOVER.md`; the tool list below reflects the original
> read-only core.

Synthetic data layer for the Exane BNPP CIB sell-side research demo: the analyst
cockpit feeds (coverage, dossier, 07:00 morning brief with the profit-warning
cascade, action inbox, agenda, jobs) and the mock market-data connectors
(consensus / price / our-estimates). ALL DATA IS SYNTHETIC — DEMO USE ONLY.

- Read-only; persistent analyst state lives in the KB (coverage-dossier skill).
- Live quotes come from the separate yahoo-finance connector; `get_price` is the
  synthetic fallback so models/notes work without it.
- OAuth optional (open when UPSTREAM_CLIENT_ID/SECRET + ZITADEL_URL unset) —
  same pattern as the RM Agent / trade-reconciliation MCPs.

## Tools (9, all read-only)
get_coverage · get_dossier(ticker) · get_morning_brief · get_action_inbox ·
get_agenda · get_jobs · get_consensus(ticker) · get_estimates(ticker) ·
get_price(ticker)

## Run locally
```bash
uv sync && uv run python src/mcp_fa_research/mcp_fa_research.py   # :8005/mcp
```

## Deploy
Same container pattern as mcp_trade_reconciliation (az acr build + Web App,
fresh timestamp tag). No database needed — the seed is in-code (`seed.py`).
