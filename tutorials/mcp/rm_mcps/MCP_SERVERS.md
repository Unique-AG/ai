# RM Agent — MCP Servers Reference (2-connector build)

_From the deployed Advisory + CRM MCP servers · 2 servers · 40 tools · as-of 2026-06-26._

This is the **consolidated** layout: the nine n8n workflows are replaced by **two**
standalone MCP servers. Connector names below are the exact server names — use them
verbatim as `data-unique-source-server` values and in skills. Each server block gives a
server-level **Description** and **System Prompt**; each tool gives its description plus a
**System Prompt: Tool Usage Instructions** and **System Prompt: Tool Response Format
Instructions** for the connector configuration.

One id everywhere — **`client_id`**. Any client tool accepts a name ("Brunner",
"Isabelle Lavanchy"), a canonical id (`CH-PB-0049217`, `PTY-0002005`, `CH-PROS-0118`), or a
legacy numeric id; all resolve to the same client. Unknown input returns an `Unknown client` hint.

## Servers

- **RM Agent - Advisory** (`https://rm-advisory-mcp.azurewebsites.net/mcp`) — 18 tools — _consolidates n8n: House Views, Client Portfolios, Transactions, Model Portfolios, Lombard Coverage_
- **RM Agent - CRM** (`https://rm-crm-mcp.azurewebsites.net/mcp`) — 22 tools — _consolidates n8n: CRM, Client Memory, Calendar; + server-side dashboard-section editor + WorldCheck person screening_

> The n8n **Portfolio Optimizer** (`propose_rebalance` / `check_suitability`) is **not** in this build — it was the Phase-2 advice engine and has no port yet.

## Recent changes (2026-06-26)

- **Consolidated** the 9 n8n workflows into these **2 Azure connectors** (FastMCP + Postgres). Bind by connector NAME.
- **`list_clients`** takes **no `input`** — call with `{}` (whole book) or `q` / `status` / `segment` / `rm` / `limit` / `skip`. (`{"input":"all"}` now errors; the cockpit binds `{}`.)
- **`list_documents`** now returns **`open_doc_payload`** per row (`{"contentId":"cont_…"}`) — the dashboard "Open" button attr-binds it (the payload-less `openDocument` + `data-unique-key` path does not open files).
- Per-client tools accept a **name**, a **client_id**, or a **legacy numeric id** (passed as `input` or `client_id`); resolve once via `get_party_identity`, reuse the `client_id`.
- Response shapes corrected to match the live tools: `recommend_model` → `{client_id, model, note}`; `get_coverage_scenario` → `options[]`; `get_risk_exposure` `currency_exposure` present for some clients; `get_attribution` → `{client_id, error}` for clients with no attribution.
- **New `edit_dashboard_section`** (CRM) — adds / removes a whole **card** (talking points, open questions, facility documents, house view, model portfolio, recommendation) on a client's investment-proposal dashboard and writes the HTML back to the KB **server-side in one call** (pass `content_id`). The agent's task scope is read-only on the dashboard document, so this tool is the **only** way to persist a section toggle — the agent must not download / edit / `unique-cli upload` the HTML. Entry point for the agent is the `dashboard-sections` skill; to change a list's *contents* (not toggle the whole card) use the client-memory `upsert_*` / `delete_*` tools.

---

## RM Agent - Advisory

**Endpoint:** `https://rm-advisory-mcp.azurewebsites.net/mcp`  ·  **Tools:** 18

**Description**

The investment side of the RM Agent, in one connector: the CIO Office's bank-wide stance (house view, themes, tactical calls); the custodied book of record (holdings, performance, attribution, risk/exposure); post-trade & lifecycle activity (settled transactions, corporate actions, elections, orders, tax lots, AML/transaction monitoring); the house model-portfolio ladder (CP-1 / BI-3 / BG-5 / GR-7) with a per-client recommendation; and Lombard (securities-backed lending) coverage scenarios. Read-only. Synthetic demo data, consistent with `/RM Client Data`. Resolve the client on `RM Agent - CRM` first.

**System Prompt**

> Use this connector for everything on the INVESTMENT side — house view, holdings, performance, transactions & lifecycle, model portfolios, and Lombard coverage. ALWAYS resolve the client on `RM Agent - CRM` first (by name or client_id) and reuse the returned `client_id` here. House-view tools are bank-wide — do NOT pass a client_id, and always quote `as_of` / `valid_until`. For portfolios, keep custodied (managed) assets distinct from held-away assets (reported by CRM), and never present a figure without its `as_of`. Surface anything that needs action — open elections with deadlines, pending orders, monitoring alerts, a Lombard facility in or near a margin call (with the shortfall amount and cure deadline) — EXPLICITLY. Ground recommendations in the house view and the client's mandate; flag a suitability gap (e.g. a model's expected max drawdown above the client's stated tolerance) rather than presenting it as decided. Report AML / monitoring alerts and their disposition factually; never speculate about financial crime. Prospects with no funded account return empty results (not errors). Read-only and non-advisory: proposing, curing, or booking is an RM + Credit/Compliance decision.

### Tools

#### `get_attribution`

[PMS 2d] Attribution: contribution by position & asset class, allocation/selection/currency effects, top contributors/detractors. Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: a client name or client_id. Use to explain what drove performance.

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, contribution_by_position[], contribution_by_asset_class[], top_contributors[], top_detractors[]}`. Clients with no attribution (e.g. prospects) return `{client_id, error}` instead.

#### `get_cio_themes`

[HV 1b] CIO investment themes / convictions: theme, horizon, conviction, rationale. Bank-wide. No arguments.

**System Prompt: Tool Usage Instructions**

> No arguments. Bank-wide.

**System Prompt: Tool Response Format Instructions**

> Returns `{house, as_of, valid_until, count, themes:[{theme, horizon, conviction, rationale}]}`.

#### `get_corporate_actions`

[T&T 7a] Corporate actions: event type, affected security, terms, key dates, mandatory/voluntary, election options, per-client entitlement. Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: a client name or client_id. Use for corporate actions on the client's holdings.

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, count, items:[{id,ticker,isin,type,status,ex_date,pay_date,gross_per_share|gross_amount|call_amount,currency,note}]}`. Flag any `status:"pending_election"` that needs a client instruction.

#### `get_coverage_scenario`

[Lombard] Static, pre-computed Lombard-facility coverage projection under a named restoration scenario. Read-only — never books a trade or moves cash. Returns baseline vs projected coverage %, band (margin/warning/safe), headroom, narrative, compliance notes and the option menu. Demo data covers client_id 50318 (Markus Brunner). scenario_id: baseline | cash_topup_100k | partial_repay_200k | trim_collateral_200k | hold.

**System Prompt: Tool Usage Instructions**

> Input (object): `{client_id|client, scenario_id}`. Resolve the client via `RM Agent - CRM` first (pass the client NAME or party id). `scenario_id` ∈ `baseline | cash_topup_100k | partial_repay_200k | trim_collateral_200k | hold`. Use to project how a Lombard facility's coverage changes under a restoration action. ALWAYS state the projected coverage % and the buffer to the margin trigger, and flag any facility in/near a margin call explicitly. Non-advisory — curing/amending is an RM + Credit decision.

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, scenario_id, baseline{coverage_pct,band,…}, projected{coverage_pct,band,lending_value,loan_outstanding,headroom}, narrative, compliance_notes, options[{scenario_id, label, projected_coverage_pct, band, selected}]}`. Bands: `margin/warning/safe`. Lead with the projected coverage % + band and the recommended action; INDICATIVE demo data — never books a trade.

#### `get_elections`

[T&T 7b] Elections/instructions: captured client election, validation status, internal cut-off vs market deadline, capture timestamp & channel. Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: a client name or client_id. Use for voluntary corporate-action elections.

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, count, items:[{id,linked_corporate_action,ticker,type,options[],elected,election_deadline,status,recommended,note}]}`. Surface open elections + their deadlines and state the recommended option.

#### `get_holdings`

[PMS 2a] Holdings: account ID, instruments (ISIN/ticker), asset class & sub-class, quantity/nominal, market value + currency, cost basis, weight %, as-of timestamp; plus held-away assets. Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: a client name or client_id. Use for the current custodied portfolio.

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, account_id, reporting_currency, as_of, total_market_value, positions[{ticker,asset_class,market_value,currency,weight_pct,...}], held_away_assets[]}`. Always cite `total_market_value` + `as_of`; keep custodied positions separate from held-away.

#### `get_house_view`

[HV 1a] CIO house view: per-asset-class stance (Overweight/Neutral/Underweight/Selective), conviction score, rationale, as-of and valid-until. Bank-wide (not per client). Call with no arguments for the full view, or pass an asset class (equities, fixed income, alternatives, fx, cash) to filter.

**System Prompt: Tool Usage Instructions**

> No arguments for the full view, or pass an asset class (equities / fixed income / alternatives / fx / cash) to filter. Bank-wide — no client_id.

**System Prompt: Tool Response Format Instructions**

> Returns `{house, as_of, valid_until, count, views:[{asset_class, stance, conviction, rationale}]}` (or a single asset-class object). Always quote `as_of` / `valid_until`.

#### `get_model_portfolio`

[MDL 1b] A model portfolio in full: code, name, risk band, reference currency, target allocation (asset class + weight %), expected return, volatility, expected max drawdown, rebalancing cadence, eligibility. Input: a model code (CP-1, BI-3, BG-5, GR-7) or name.

**System Prompt: Tool Usage Instructions**

> Input: a model code/name ('BI-3', 'Balanced Income') or a risk band (conservative / balanced-conservative / balanced / growth).

**System Prompt: Tool Response Format Instructions**

> Returns the full model `{code,name,risk_band,reference_currency,allocation[{asset_class,weight}],expected_return_pa,volatility_pa,expected_max_drawdown,rebalancing,eligible}`.

#### `get_orders`

[T&T 7c] Orders/trades: proposed/actual order, estimated cost/price, pre-trade compliance result, execution status. Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: a client name or client_id. Use for proposed / working / filled orders.

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, count, items:[{id,ticker,side,order_type,quantity?,gross_amount,currency,status,placed,filled?,pre_trade_compliance,note}]}`. Always show `pre_trade_compliance` and `status`.

#### `get_performance`

[PMS 2c] Performance: period returns gross & net (MTD/QTD/YTD), since-inception/annualised, benchmark, relative (excess) return, TWR/MWR basis. Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: a client name or client_id. Use for time-weighted returns.

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, basis, periods{MTD/QTD/YTD{gross,net,benchmark?,relative?}}, since_inception{...}, benchmark_name}`. Always present net alongside gross, plus the benchmark / relative where given.

#### `get_portfolio_transactions`

[PMS 2b] Settled transactions: trade & settlement date, type, instrument+qty+price, gross/net amount, counterparty, status. Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: a client name or client_id. Use for the client's settled transaction history.

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, count, items:[{trade_date,type,ticker?,gross_amount,currency,counterparty?,status}]}`. Settled activity only, chronological.

#### `get_risk_exposure`

[PMS 2e] Risk/exposure: asset allocation actual vs target, currency exposure, concentration, liquidity profile. Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: a client name or client_id. Use for allocation-vs-target and risk flags.

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, asset_allocation[{asset_class,actual_pct,target_pct}], flags[], currency_exposure{} (present for some clients)}`. Surface `flags` (overweights, concentrations) explicitly.

#### `get_tactical_calls`

[HV 1c] Tactical allocation calls: dimension, call (over/under-weight/hedge), detail, magnitude, conviction, rationale. Bank-wide. No arguments.

**System Prompt: Tool Usage Instructions**

> No arguments. Bank-wide.

**System Prompt: Tool Response Format Instructions**

> Returns `{house, as_of, valid_until, count, calls:[{dimension, call, detail, magnitude, conviction, rationale}]}`.

#### `get_tax_lots`

[T&T 7d] Tax-lot & cost: tax lots (date/cost/qty), unrealised gain/loss, estimated transaction cost, estimated tax impact. Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: a client name or client_id. Use for tax lots, cost basis, and tax impact.

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, lots:[{isin,ticker,acquired,quantity?,cost_total,market_value,unrealised,currency,note?}], unrealised_gain_loss{total,currency}, estimated_transaction_cost, estimated_tax_impact, note}`. Note the CH private-investor CGT exemption where the data states it.

#### `get_transaction_monitoring`

[T&T 7e] Transaction monitoring: actual activity summary, expected activity profile, anomaly/deviation flags. Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: a client name or client_id. Use for AML / transaction-monitoring status.

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, alerts:[{id,date,type,amount,currency,rule,disposition,source_of_wealth|purpose,cleared_by,cleared_date}], open_cases, status, note?}`. Present alerts and disposition factually; `cleared` means resolved.

#### `list_model_portfolios`

[MDL 1a] Model-portfolio catalogue: code, name, risk band, reference currency, expected return, volatility, expected max drawdown, rebalancing cadence. No arguments.

**System Prompt: Tool Usage Instructions**

> No arguments. Use for the model catalogue.

**System Prompt: Tool Response Format Instructions**

> Returns `{house, as_of, count, models:[{code,name,risk_band,reference_currency,expected_return_pa,volatility_pa,expected_max_drawdown,rebalancing}]}`.

#### `recommend_model`

[MDL 1c] Recommend a model for a client by mapping their captured risk profile/objective (CRM mandate) to the model ladder. Returns recommended model code, the model, and a suitability note. Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: a client name or client_id (resolved via the CRM mandate on `RM Agent - CRM`).

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, model, note}` — `model` is the recommended model code (e.g. BG-5) and `note` is the suitability note (states if the model's expected max drawdown exceeds the client's stated tolerance).

#### `Reset_Demo_Data`

Reset this server's demo data to its baseline. DESTRUCTIVE: truncates the Advisory tables and re-inserts the original seed rows; any changes made during the demo are discarded. Use between demo runs for a clean, predictable starting state.

**System Prompt: Tool Usage Instructions**

> No input. Operator/demo tool only — call BETWEEN demo runs to restore the baseline. Never call it as part of answering a client question.

**System Prompt: Tool Response Format Instructions**

> Returns `{reset:true, tables:{...row counts...}, total_rows, note}`. Confirm the reset succeeded and the row counts look right; do not surface to the client.

---

## RM Agent - CRM

**Endpoint:** `https://rm-crm-mcp.azurewebsites.net/mcp`  ·  **Tools:** 22

**Description**

The relationship side of the RM Agent, in one connector: the client system of record (legal identity, KYC identifiers, legal-entity & ownership/UBO chain, relationship & RM ownership, mandate & objectives, interaction history, the client-book roster, and the per-client KB document catalog); the EDITABLE per-client lists shown live on the investment-proposal dashboard (talking points, open questions, facility documents); a server-side dashboard editor (`edit_dashboard_section`) that adds / removes whole cards on that dashboard; and the RM calendar (upcoming & past client meetings). Mostly read-only — the client-memory `upsert_*` / `delete_*` tools and `edit_dashboard_section` are the only writers. Synthetic demo data, consistent with `/RM Client Data`.

**System Prompt**

> Use this connector to establish WHO a client is, to manage the dashboard's editable lists, and to read the calendar — never for holdings, prices, performance, or recommendations (use `RM Agent - Advisory`). ALWAYS resolve the client here first (by name or client_id) and reuse the returned `client_id` across this connector and `RM Agent - Advisory`. Treat identity / relationship / mandate as authoritative; an empty field on a wired client means 'not yet captured' (signal), not 'unknown' — say so rather than inventing a value. Never infer suitability or returns from CRM data. EDITABLE MEMORY: the talking points / open questions / facility documents on the proposal dashboard live here — read with the `get_*` / `list_documents` tools (each row has a `position` + `text`/`title`), then `upsert_*` to add a row (next free position) or change one (existing position), or `delete_*` to remove a row by position; keep talking points / questions ≤200 chars and ≤20 per client; for documents pass a valid `cont_…` `contentId` from `list_available_documents`. The dashboard reads these live — never edit a file or the dashboard HTML. SECTION TOGGLE: to add or remove a WHOLE card (section) of the dashboard — e.g. drop the open-questions card or bring the talking-points card back — call `edit_dashboard_section` (one call, writes server-side); never download / edit / `unique-cli upload` the HTML yourself (your task scope is read-only on it). CALENDAR: present times in the event's stated timezone and lead with the soonest relevant meeting. `list_available_documents` is the read-only catalog of a client's KB files (pick contentIds from it when curating the document list).

### Tools

#### `delete_document`

Delete one pinned document by position for a client.

**System Prompt: Tool Usage Instructions**

> WRITE (one document). Input: `client_id` (or `input`) + `position`. Removes a document from the dashboard's Facility Documents.

**System Prompt: Tool Response Format Instructions**

> Deletes the matching row (`{client_id, position, deleted:true}`).

#### `delete_open_question`

Delete one open question by position for a client.

**System Prompt: Tool Usage Instructions**

> WRITE (one question). Input: `client_id` (or `input`) + `position`. Removes that open question.

**System Prompt: Tool Response Format Instructions**

> Deletes the matching row (`{client_id, position, deleted:true}`).

#### `delete_talking_point`

Delete one talking point by position for a client.

**System Prompt: Tool Usage Instructions**

> WRITE (one point). Input: `client_id` (or `input`) + `position`. Removes that talking point. Call `get_talking_points` first to find the position.

**System Prompt: Tool Response Format Instructions**

> Deletes the matching row (`{client_id, position, deleted:true}`); the dashboard drops it on refresh.

#### `edit_dashboard_section`

[DASH 1] Add or remove a WHOLE section (card) of a client's investment-proposal dashboard — recommendation, house view, model portfolio, talking points, open questions, facility documents — and write the HTML back to the Knowledge Base in one call (no file download/upload on the agent's side). Removed cards stay in the dashboard's embedded section library, so `add` restores the exact card. To change a list's CONTENTS rather than toggle the whole card, use the client-memory `upsert_*` / `delete_*` tools instead.

**System Prompt: Tool Usage Instructions**

> WRITE (whole card, server-side). Input: `client_id`; `action` (`list` | `remove` | `add`); `section` (a key — `recommendation` / `house_view` / `model_portfolio` / `talking_points` / `open_questions` / `facility_documents` — or a card id like `mod-5`; omit for `list`); and `content_id` (the dashboard's `cont_…` id — it's in the Edit-with-AI prompt; pass it so the exact file is edited). Make ONE call — it toggles the card and saves the file with the server's own credentials. Do NOT download / edit / `unique-cli upload` the dashboard (the agent's task scope is read-only on that document). If it returns "MCP tool is not enabled", stop and tell the RM the tool needs enabling/re-syncing on this connector — do not fall back to the CLI.

**System Prompt: Tool Response Format Instructions**

> `list` → `{client_id, present:[{id,key}], addable:[{id,key}]}`. `remove`/`add` → `{client_id, section, id, action, changed:true, note}` (or `changed:false` with a `note` — e.g. "already removed" / "already present"). On success tell the RM to **Refresh** the dashboard.

#### `get_entity_ownership`

[CRM 1c] Entity & ownership: entity type, beneficial owners, directors, controllers, signatories, ownership depth. Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: a client name or client_id. Use to understand the legal-entity / ownership (UBO) structure.

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, entity_type, beneficial_owners[], directors[], controllers[], authorised_signatories[], ownership_structure_depth, note}`. For individuals these arrays are empty (the note says so). An empty UBO list on a wired entity means 'to be verified', not 'none'.

#### `get_history`

[CRM 1f] History: interaction log/meeting notes, open tasks, life events, complaints. Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: a client name or client_id. Use to prep for a meeting or summarise the relationship.

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, interaction_log[], open_tasks[{task,due,status}], life_events[], complaints[]}`. Lead with the most recent interactions and any overdue/open tasks.

#### `get_identifiers`

[CRM 1b] Identifiers: passport, national ID, LEI, company registration, internal party ID. Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: a client name or client_id. Use for KYC / onboarding identifier lookups.

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, passport, national_id, lei, company_registration, internal_party_id}` (only the applicable fields are present). Do not expose full document numbers unless the task requires it.

#### `get_mandate_objectives`

[CRM 1e] Mandate & objectives: mandate type, investment objective, risk profile, horizon/liquidity, constraints, reference currency, fee schedule. Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: a client name or client_id. Use to anchor any advice to the client's mandate.

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, mandate_type, investment_objective, risk_profile, investment_horizon_liquidity, constraints_exclusions[], reference_currency, fee_schedule?}`. Treat `risk_profile`, `constraints_exclusions`, and `reference_currency` as binding. Null fields ⇒ not yet captured (prospect).

#### `get_meetings`

[CAL 1a] Calendar meetings (synthetic, consistent with RM Client Data). Input: a client name or client_id (that client's meetings); an RM username (marc.dubois / daniel.frei); or 'week' / omit for all upcoming meetings.

**System Prompt: Tool Usage Instructions**

> Input: a client name/id, an RM username (e.g. marc.dubois), 'week', or omit for all upcoming. Resolve client names the same way as the identity tools.

**System Prompt: Tool Response Format Instructions**

> Returns `{count, meetings:[{...,start/start_at,title,type,client,client_id,rm,channel,agenda,status}], client_id?}`, sorted by start time. Lead with the soonest relevant meeting; present times in the event's timezone.

#### `get_next_meeting`

[CAL 1b] The next upcoming meeting for a client. Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: a client name or client_id. A named client that doesn't resolve returns an `Unknown client` hint (not the global next meeting).

**System Prompt: Tool Response Format Instructions**

> Returns `{next_meeting:{...}|null, client_id?}`. If `next_meeting` is null there is nothing upcoming for that client.

#### `get_open_questions`

Get the client's editable open questions (ordered list). Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: `client_id` (or `input`). Reads the client's OPEN QUESTIONS — the live list shown on the dashboard. Change with `upsert_open_question` / `delete_open_question`.

**System Prompt: Tool Response Format Instructions**

> Returns a top-level array of rows (each `{client_id, position, text}`), listed by `position`.

#### `get_party_identity`

[CRM 1a] Party identity: full legal name, aliases, DOB, place of birth, gender, nationalities, country of residence, tax residences + TIN. Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Resolve a client by name or client_id and confirm their legal identity. Input: `{"input":"<name or client_id>"}`. Call this first to make sure you have the right party.

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, full_legal_name, aliases, date_of_birth, place_of_birth, gender, nationalities[], country_of_residence, tax_residences[]}`. Lead with legal name + DOB + nationalities; surface tax residence for cross-border context.

#### `get_relationship`

[CRM 1d] Relationship: client/prospect status, owning RM/team/booking centre, segment, referral, related parties, languages, contact + preferred channel. Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: a client name or client_id. Use for relationship context and routing.

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, client_vs_prospect, owning_rm_team_booking_centre{rm,team,booking_centre}, client_segment, referral_source, languages[], contact{...}}`. Use status (client vs prospect), segment, and owning RM to set tone and routing.

#### `get_talking_points`

Get the client's editable talking points (ordered list). Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: `client_id` (or `input`) — a client name or id. Reads the client's meeting TALKING POINTS — the live list shown on the investment-proposal dashboard. Each row is one point. Change with `upsert_talking_point` / `delete_talking_point`.

**System Prompt: Tool Response Format Instructions**

> Returns a top-level array of rows (each `{client_id, position, text}`), which the dashboard lists by `position`.

#### `list_available_documents`

[CRM 1m] CATALOG — every document in a client's KB folder with its contentId. Pass client_id (or name). Returns {client_id, count, documents:[{title, contentId, kind}]}. Use this to discover what files exist for a client.

**System Prompt: Tool Usage Instructions**

> Input: a client name or client_id. Returns the full CATALOG of documents in that client's KB folder, each with its contentId — the candidate set for the dashboard's Facility Documents. Use it when curating that list: read the catalog, pick the contentIds the RM wants, then add them with `upsert_document` (same connector).

**System Prompt: Tool Response Format Instructions**

> Returns `{client_id, count, documents:[{title, contentId, kind}], items}` where `title` is a readable form of the filename.

#### `list_clients`

[CRM 1g] Client book / roster + SEARCH (RM cockpit & client lookup). Optional args: q (free-text substring over name/client_id/segment/rm/status), status (client|prospect), segment (e.g. UHNW), rm, limit, skip. Returns {total, count, skip, limit, clients[]}.

**System Prompt: Tool Usage Instructions**

> Roster + search. `{}` (no args) → the whole book; or search/filter with `q` (free-text over name/id/segment/rm/status), `status` (client|prospect), `segment`, `rm`, and `limit`/`skip` for pagination — e.g. `{"q":"Brunner"}`, `{"segment":"UHNW"}`. Use to find clients at scale (the chat search) and to populate the cockpit.

**System Prompt: Tool Response Format Instructions**

> Returns `{total, count, skip, limit, clients:[{client_id, name, status, segment, rm, value_label, model, dashboard_path, content_id, open_doc_payload, …}]}`. `total` = full matches, `count` = returned this page. Each row carries the path + contentId to that client's pregenerated dashboard; render as a roster, not prose.

#### `list_documents`

Get the client's pinned documents (ordered list with title + contentId). Input: client name or client_id.

**System Prompt: Tool Usage Instructions**

> Input: `client_id` (or `input`). Returns the FACILITY DOCUMENTS shown on the proposal dashboard. Change with `upsert_document` / `delete_document`. (To discover candidate files + contentIds, use `list_available_documents`.)

**System Prompt: Tool Response Format Instructions**

> Returns a top-level array of rows (each `{client_id, position, title, contentId, open_doc_payload}`), listed by `position`. `open_doc_payload` is a `{"contentId":"cont_…"}` JSON string the dashboard's Open button attr-binds for openDocument (same pattern as list_clients.open_doc_payload).

#### `Reset_Demo_Data`

Reset this server's demo data to its baseline. DESTRUCTIVE: truncates the CRM tables and re-inserts the original seed rows — in particular the editable client memory (talking points / open questions / pinned documents) is restored (rows added during the demo are removed and deleted rows come back). Use between demo runs.

**System Prompt: Tool Usage Instructions**

> No input. Operator/demo tool only — call BETWEEN demo runs to restore the baseline (including the editable client memory). Never call it as part of answering a client question.

**System Prompt: Tool Response Format Instructions**

> Returns `{reset:true, tables:{...row counts...}, total_rows, note}`. Confirm the reset succeeded; do not surface to the client.

#### `screen_person`

Screens a person or entity against the WorldCheck (LSEG) SYNTHETIC watchlist and returns partial + exact matches. Required: `name` (Latin or original script). Optional refinements: `country`, `nationality`, `date_of_birth` (+`dob_tolerance_years`), `place_of_birth`, `gender`, `entity_type` (Individual/Entity), identifiers `passport_number` / `national_id` / `tax_id`, `wc_uid` (direct fetch), `threshold` (default 0.45), `max_results` (default 25). SYNTHETIC data — KYC/AML tool testing only.

**System Prompt: Tool Usage Instructions**

> Screen a party against the synthetic WorldCheck watchlist for KYC/AML/PEP/sanctions checks — NOT the client system of record (that's `get_party_identity`). Pass at least `name` (or a `wc_uid` to fetch one record). Add whatever refinements you have: `country`/`nationality` (name, ISO or abbrev), `date_of_birth` (many formats; `dob_tolerance_years` for approximate years), and identifiers `passport_number`/`national_id`/`tax_id` — an exact identifier hit is near-conclusive even if the name spelling differs. SYNTHETIC data: always flag that a hit must be verified before any decision.

**System Prompt: Tool Response Format Instructions**

> Returns `{source, searched{…echoed inputs…}, records_screened, match_count, matches:[{match_score (0-1), name_score, match_type (uid_lookup|exact_identifier|exact_name|partial), matched_on[], record{wc_uid, primary_name, aliases, is_pep, pep_class, is_sanctioned, sanctions_lists, adverse_media_topics, risk_rating, nationalities, identifiers, linked_associates, sources, …}}], message}`. Lead with the highest `match_score` + its `match_type`; surface PEP / sanctions / adverse-media flags. Empty `matches` = no hit in the synthetic set.

#### `upsert_document`

Create or update one pinned document (title + contentId) at a position for a client.

**System Prompt: Tool Usage Instructions**

> WRITE (one document). Input: `client_id` (or `input`), `position`, `title`, `contentId` (a valid `cont_…` from `list_available_documents`). Adds a document to the dashboard's Facility Documents at a new position, or changes one at an existing position.

**System Prompt: Tool Response Format Instructions**

> Upserts the row `{client_id, position, updated:true, title, contentId}`; the dashboard shows it on refresh.

#### `upsert_open_question`

Create or update one open question at a position for a client.

**System Prompt: Tool Usage Instructions**

> WRITE (one question). Input: `client_id` (or `input`), `position` (next free number to add, or an existing one to change), `text` (≤200 chars). Matches on client_id + position; read first with `get_open_questions`. Keep ≤20 per client.

**System Prompt: Tool Response Format Instructions**

> Upserts the row and echoes the stored `{client_id, position, updated:true, text}`; the dashboard shows it on refresh.

#### `upsert_talking_point`

Create or update one talking point at a position for a client.

**System Prompt: Tool Usage Instructions**

> WRITE (one point). Input: `client_id` (or `input`), `position` (the slot — next free number to ADD, or an existing number to CHANGE), `text` (≤200 chars). Matches on client_id + position. Call `get_talking_points` first to see current positions. Keep ≤20 points per client.

**System Prompt: Tool Response Format Instructions**

> Upserts the row (insert if the position is new, else update) and echoes the stored `{client_id, position, updated:true, text}`. The dashboard shows it on refresh.

