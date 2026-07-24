# dashboard-v005-astro

The account-remediation dashboard, authored as Astro components and compiled
down to a single zero-JS `data-unique-*` static HTML artifact. This is the
primary implementation — the earlier Python/`build.py` string-templating
approach (`../archive/dashboard-v005/`) has been retired in its favour and is
kept around only for reference.

Two bets drove the rewrite:

1. **Author the dashboard as Astro components** instead of `build.py`'s
   string-template partials — real props/JSX-ish syntax and a type-checked
   case registry, compiled down to the same zero-JS `data-unique-*` static
   HTML artifact.
2. **Abstract the data-unique-\* contract** so the exact same markup can be
   driven by either the live MCP connector (platform artifact) or local
   mock data (offline, interactive preview) — no markup forked between the
   two, no hand-authored fixtures that drift from the schema.

Page coverage: the attention rail (list), KPI tiles (count), the portfolio
table (status/risk menus, reset action), the `:target`-routed client detail
page with all 8 profile sections (Executive Summary, Client Identity,
History, Documents and KYC, Portfolio and Mandate, Portfolio Performance and
Benchmark, Holdings and Categorization, Suitability Profile), and the
case-driven action-bar/figure components for all 6 use cases. See
[Known gaps](#known-gaps) below for what's still scoped down.

## The core idea: one markup, three hosts

Every `data-unique-list`/`data-unique-action` element in `src/pages/index.astro`
is **byte-for-byte identical** across all three builds. The only difference is
what gets appended to `<body>`:

| | `npm run build:live` | `npm run build:preview` | `npm run build:live-local` |
| --- | --- | --- | --- |
| Markup | same | same | same |
| Data | none baked in — platform host binds it live | `src/data/mock.json`, dumped from the real dataset | none baked in — fetched live over HTTP |
| Script | **none** — `grep -c '<script' dist/live/index.html` → `0` | `public/mock-host.js` (~230 lines, vanilla JS, zero deps) | `public/mcp-live-host.js` (real Streamable HTTP, zero deps) |
| Use | the platform artifact | open directly in a browser, or `npm run dev`, for local/offline review | open in a browser against a real local `mcp_sqlite_excel` server — for exercising the actual backend, no platform in between |

### `live-local`: talking to a real local MCP server, no platform in between

```bash
# in tutorials/mcp/mcp_sqlite_excel/
AUTH_DISABLED=true UNIQUE_MCP_LOCAL_BASE_URL=http://127.0.0.1:8004 uv run mcp-sqlite-excel

# in this folder:
npm run build:live-local   # → dist/live-local/index.html
# open dist/live-local/index.html directly, or npm run dev:live-local
```

`public/mcp-live-host.js` speaks real MCP over Streamable HTTP (JSON-RPC 2.0,
session handshake, SSE framing) directly to that server — the same wire
protocol a real connector uses, just called straight from the browser since
`AUTH_DISABLED=true` also disables the Zitadel OIDC layer that would
otherwise sit in front of it. Two things worth knowing:

- **CORS must expose `mcp-session-id`.** Streamable HTTP returns the session
  id as a response header on `initialize`, which the client must echo back on
  every later request — but response headers are invisible to browser JS
  unless the server explicitly lists them in `Access-Control-Expose-Headers`.
  `mcp_sqlite_excel.py`'s CORS middleware now sets
  `expose_headers=["mcp-session-id"]` for exactly this reason; without it
  every call after `initialize` 400s with "Missing session ID" (works fine
  from `curl`/Node, since neither enforces CORS — only caught this by
  actually loading the build in a browser).
- **`escalate_row`/`reset_from_excel` elicit mid-call.** They call
  `ctx.elicit(...)` server-side, which arrives as a JSON-RPC request
  (`elicitation/create`) on the *same* SSE stream opened for the
  `tools/call`, must be answered with a *separate* POST, after which the
  original stream resumes and emits the real result. `mcp-live-host.js`
  renders a small modal from the server's `requestedSchema` (whatever fields
  it asks for — recipient email, note, ...) to answer it, so escalating a
  card here sends a **real** notify-email side effect on the local server,
  same as it would from a real chat connector.

Override the target server per page load without rebuilding:
`dist/live-local/index.html?mcp=http://host:port/mcp` (defaults to
`config.mcp_local_url`, `http://127.0.0.1:8004/mcp`).

`npm run verify:live-local` drives this end-to-end in headless Chromium
against a *real* running server (hydration + the full escalate/elicitation
round-trip) — unlike `npm run verify`, which only exercises jsdom + mock
data. It requires the server above to actually be running; it escalates one
real row via the UI, then reverts it (`update_row`, no elicitation needed)
once the check passes, so the shared dataset ends up unchanged.

`public/mock-host.js` is a tiny, generic interpreter for the
`data-unique-*` contract — it isn't specific to this dashboard's markup. It:

- scans the DOM for `[data-unique-list]` containers, reads their
  `data-unique-source-tool`/`-args`, and re-derives rows from
  `window.__MOCK_DATA__` (keyed by **table**, e.g. `clients`) — a ~15-line
  client-side mirror of `mcp_sqlite_excel`'s `repository.list_rows`/`count_by`
  (filter + limit, or group-by-column)
- clones each `<template data-unique-item>` once per row and fills
  `data-unique-field`/`data-unique-attr-*`, using the same interpolation
  rule as the real platform host: a bare value (no `{...}`) is a field-name
  lookup, a value containing `{field}` is a template string with just that
  placeholder substituted (this is the exact rule behind the "prompt
  arrives unfilled" bug fixed earlier on `../archive/dashboard-v005/`)
- intercepts clicks on `[data-unique-action]`: `callTool` mutates the
  matching row(s) in `window.__MOCK_DATA__` and re-hydrates every list named
  in `data-unique-source-refresh`; `sendPrompt` shows the fully-resolved
  prompt text in a corner toast — a good way to eyeball payload
  interpolation without spending a real chat turn

Because mutations happen against one canonical `clients` array and every
list re-queries it, escalating a client in the attention rail immediately
updates the KPI tiles and empties out of the rail too — same as the real
backend, no per-list bookkeeping needed.

## Layout

```
dashboard-v005-astro/
  astro.config.mjs        # output: static, build.inlineStylesheets: 'always'
  package.json             # build:live / build:preview / dev / verify
  scripts/
    dump_mock_data.py      # dumps the *real* clients table → src/data/mock.json
    verify-preview.mjs     # jsdom smoke test for mock-host.js (npm run verify)
    screenshot.mjs          # playwright: renders dist/preview → screenshots/*.png (npm run screenshot)
  public/
    mock-host.js           # preview-only; never referenced by build:live
    mcp-live-host.js       # live-local only; browser-side Streamable HTTP host
  src/
    data/
      cases.json            # registry of the 6 use cases (rule_code, tags, prompts, open_sections)
      config.json            # mcp_server / rm_name / page_title / poll_ms
      mock.json               # generated — git-ignore-worthy, regen with npm run mock:data
    styles.css               # design system — canonical here, no longer shared via ../archive/
    lib/
      cases.js              # rulePairs/renderCaseCss/renderOpenSectionsCss
      contract.ts           # typed builders for data-unique-list/callTool/sendPrompt attrs
      mode.ts               # DASHBOARD_MODE parsing + preview/live-local config loading
    components/
      ModeBanner.astro     # build-mode banner: live / preview / live-local
      HostScripts.astro    # build-mode script injection: none / mock host / live-local host
      AttentionRail.astro   # "Needing attention" section (live clients + quick Compliant/Escalate actions)
      PortfolioPanel.astro  # "Your portfolio" section: KPIs, client table, reset-demo-data toolbar
      ClientDetailPage.astro # the :target-routed client detail page (header, actionbar, 8 profile sections, case figures)
      CaseActionBar.astro   # case-driven action-bar component
      CaseFigure.astro      # case-driven figure/widget component (uses FigureRows)
      DataList.astro        # [data-unique-list] container powered by lib/contract.ts
      EditableCell.astro    # portfolio table's status/risk dropdown-menu <td> (data-driven options list)
      FieldGrid.astro       # .fldgrid of .fld label/value rows, data-driven
      FigureRows.astro      # the fig{N}_label/value/pct/status figrow block, shared by CaseFigure + client-page sections
      Section.astro         # <details class="card sec"> chrome (chevron/title/meta/body) shared by every client-page section
    pages/index.astro        # page shell: head + named sections + clientPages list + HostScripts
  dist/
    live/index.html         # → the platform artifact
    preview/index.html      # → open directly in a browser, fully interactive
```

## Running it

```bash
npm install                # once

npm run build:live         # → dist/live/index.html   (0 <script> tags)
npm run build:preview      # → dist/preview/index.html (mock data + mock-host.js)
npm run dev                 # astro dev, preview mode, live-reload while you edit

npm run verify              # jsdom smoke test: lists hydrate, callTool mutates + refreshes,
                             # sendPrompt payloads have no leftover {placeholder}s

npm run mock:data           # regenerate src/data/mock.json from the real dataset
                             # (uv run python scripts/dump_mock_data.py under the hood)

npm run screenshot          # renders dist/preview headlessly (playwright) →
                             # screenshots/console.png + client.png, for visual review
                             # without opening a browser yourself
```

Open `dist/preview/index.html` directly in a browser (no dev server
needed) to click around with real client names, escalate a card, and watch
the KPI tiles and attention rail update.

## Known gaps

- All 8 client-page sections are populated with real per-client data (not
  just the flagged-case row) — but every section ships with the HTML `open`
  attribute so all of them render expanded on every client, per current
  product direction ("for now you can always show them"). The
  `open_sections` CSS mechanism that force-opens just the section relevant
  to a case (see `src/data/cases.json`) is wired through but has no visible
  effect yet since everything is already open — flip a section's `open`
  attribute off to see it kick in.
- Client-page fields not sourced from a real dataset column (e.g. some
  `na-field`s) still render as an em dash rather than being hidden.

**A real bug this scoping caught:** the client-page list (`.client-pages`,
`display: contents`) was first nested *inside* `<main class="page
view-main">`. That's invisible in a DOM inspection (`display: contents`
elements still show their children in place) but broke the `:target`
router — `body:has(.view-client:target) .view-main { display: none }`
hid the entire ancestor, so the "active" client page had `display: grid`
computed on itself yet rendered with a `0×0` box, because a `display:
none` ancestor always wins. `npm run verify`'s jsdom checks didn't catch
it (jsdom doesn't compute layout); a real headless-browser screenshot
(`npm run screenshot`) did immediately. Fixed by moving `.client-pages` to
be a sibling of `.view-main`.

## Possible next steps

- Promote `public/mock-host.js` to a shared, dashboard-agnostic asset —
  nothing in it is Astro- or v005-specific; other `mcp_sqlite_excel`-backed
  dashboards could reuse it as-is.
- `scripts/dump_mock_data.py`'s pattern (call the real repository, dump
  once, key by table) generalises to any `mcp_sqlite_excel`-backed
  dashboard — worth lifting into a small shared helper if a second one
  shows up.
