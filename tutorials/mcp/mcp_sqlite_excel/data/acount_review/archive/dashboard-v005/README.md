# Account Review console — v005

Multi-file HTML sources, combined into **one** platform file. **All business
data is live from MCP** — there is no agent “rebuild HTML” step.

This is the dashboard **creator** for the 6 RM Account-Remediation use cases
(see the Product doc: _RM Account-Remediation Dashboard — Use Cases_). All 6
cases ship in every build; the reusable client-detail page, attention rail
and portfolio table stay identical across cases — only the **smart action**
(the bit that's actually different per use case) swaps in live, per row,
based on that row's `rule_code`. See [Cases](#cases--use-cases) below.

## Layout

```
dashboard-v005/
  build.py                 # combine pages + expand cases + inline CSS
  src/
    config.json            # ← MCP server id & other build variables
    config.example.json    # template for new environments
    cases.json             # ← the 6 use cases: tag, icon, figure, sendPrompt instructions
    shell.html
    styles.css
    templates/
      actionbar_case.html      # 1 reusable partial → expanded once per rule_code
      actionbar_case_dual.html # variant for cases with 2 actions (e.g. regulatory change)
      figure_case.html         # 1 reusable partial → the case-specific figure section(s)
    pages/
      manifest.json
      clients.html
      main.html
  ../dashboard-v005.html   # PLATFORM ARTIFACT
```

## Configuration

Edit `src/config.json`:

| Key | Placeholder | Purpose |
| --- | --- | --- |
| `mcp_server` | `__MCP_SERVER__` | Unique MCP connector id |
| `rm_name` | `__RM_NAME__` | Greeting name |
| `page_title` | `__PAGE_TITLE__` | HTML `<title>` |
| `poll_ms` | `__POLL_MS__` | `data-unique-source-poll` interval |
| `connectors_online` | `__CONNECTORS_ONLINE__` | Footer label |
| `output` | *(n/a — destination path, not a placeholder)* | Where the built HTML is written, relative to this folder unless absolute. Default: `../dashboard-v005.html` |

Overrides (later wins):

1. `src/config.json`
2. Env: `DASHBOARD_MCP_SERVER`, `DASHBOARD_RM_NAME`, `DASHBOARD_PAGE_TITLE`,
   `DASHBOARD_POLL_MS`, `DASHBOARD_CONNECTORS_ONLINE`, `DASHBOARD_OUTPUT`
3. CLI flags

## Build

```bash
python build.py
python build.py --mcp-server mcp_thvxcf56tka96a8lmv2ilwfd
python build.py --print-config
DASHBOARD_MCP_SERVER=mcp_xxx python build.py
```

→ `../dashboard-v005.html` (or whatever `output` resolves to — see below)

### Creating a new/named dashboard

`output` makes the destination file configurable, so you can produce more
than one dashboard artifact from this same `src/` without overwriting the
default one — e.g. a per-demo or per-RM variant:

```bash
# One-off, via CLI flag (highest precedence):
python build.py --output ../dashboard-onboarding-demo.html

# Or via env:
DASHBOARD_OUTPUT=../dashboard-onboarding-demo.html python build.py

# Or persist it by copying config.json → e.g. config.onboarding.json and
# pointing DASHBOARD_MCP_SERVER / --mcp-server + DASHBOARD_OUTPUT at it.
```

Relative paths resolve against this folder (`dashboard-v005/`), so
`"output": "../dashboard-foo.html"` always lands in `data/acount_review/`
regardless of your current working directory when you run `build.py`.

## Live bindings

| UI | MCP tool | List id |
| --- | --- | --- |
| Client detail pages | `list_rows` (clients) | `clientPages` |
| Attention rail | `list_rows` (Needs Remediation) | `attentionLive` |
| KPI tiles | `count_by` (status) | `statusKpis` |
| Portfolio table | `list_rows` (clients) | `clientsLive` |

## Cases — the 6 use cases

`src/cases.json` is the single registry for the 6 RM use cases. Each entry:

| Field | Purpose |
| --- | --- |
| `rule_codes` | One or more `clients.rule_code` values this case handles (e.g. adverse-media and PEP both map to one case) |
| `tag` / `icon` | Shown in the case badge (attention card, crit banner, executive summary) |
| `figure_title` | Heading of the case's figure section, rendered as an accordion item (e.g. "Portfolio and Mandate", "Documents & KYC") — reads `fig1..3_*` fields |
| `figure_bars` | Optional — set on a case to render its figure's 3 rows as progress bars (currently: portfolio allocation) instead of plain label/value |
| `figure2_title` | Optional — a **second** figure section alongside the first, reading `perf1..3_*` fields instead of `fig1..3_*` (currently only the portfolio-breach case: "Portfolio Performance vs Benchmark") |
| `open_sections` | Optional — keys of the *generic* client-page sections (see below) to force expanded when this case's `rule_code` is live, e.g. `["history"]` |
| `instructions` | The case-specific closing instruction appended to the single "Analyse with AI" `sendPrompt` |
| `dual_action` | Optional — replaces the single button with two (e.g. regulatory change's "Email client" vs "Escalate to compliance"), each its own label/toast/instructions |

At build time, `build.py`:

1. Reads `src/templates/actionbar_case.html` (or `actionbar_case_dual.html`
   for a case with `dual_action`) — reusable action-bar partials — and
   expands one per `rule_code` into `clients.html` (replacing the
   `<!-- __CASE_ACTIONBARS__ -->` marker inside the shared action bar shell).
2. Reads `src/templates/figure_case.html` — **one** reusable, parametrized
   accordion-section partial — and expands it once per `rule_code` (and a
   second time, with the `perf`-prefixed fields, for any case with a
   `figure2_title`), replacing the `<!-- __CASE_FIGURES__ -->` marker in
   `clients.html`.
3. Generates the matching `[data-rule="…"]` visibility, badge-label,
   progress-bar and force-open CSS from the same registry (replacing the
   `__CASE_VISIBILITY_CSS__` / `__CASE_BADGE_CSS__` / `__CASE_BARS_CSS__` /
   `__CASE_OPEN_SECTIONS_CSS__` markers in `styles.css`).

### Client-detail sections & "only the relevant ones open"

Every client page is a stack of collapsible `<details class="sec">`
accordion items:

| Section | `data-key` | Default | Opens for |
| --- | --- | --- | --- |
| Executive summary | `exec-summary` | always open | every case |
| Client identity | `identity` | always open | every case |
| History (last/next reviewed, KYC refresh due) | `history` | collapsed | forced open when a case lists `"history"` in `open_sections` (adverse-media) |
| Documents and KYC (screening + docs on file, merged) | `docs-kyc` | collapsed | forced open when a case lists `"docs-kyc"` (document/KYC refresh) |
| *(case figure)* — one per `rule_code`, e.g. "Portfolio and Mandate", "Holdings and Categorization" | n/a (visibility keyed on `data-rule`, not `data-key`) | shown + open only for its matching case | that case only |
| *(case figure 2)* — only for cases with `figure2_title`, e.g. "Portfolio Performance vs Benchmark" | n/a | shown + open only for its matching case | that case only |

"Force open" is pure CSS (`.detail[data-rule="…"] .sec[data-key="…"] > .sec-body { display: block }`
plus the matching chevron rotation) generated by
`build.py`'s `render_open_sections_css` from each case's `open_sections` —
no JavaScript. Sections without a matching rule stay ordinary,
user-collapsible `<details>`; the case figure(s) are always rendered
already expanded, since they only exist in the DOM for their one matching
case in the first place (same `[data-rule]` visibility trick as the action
bar).

The figure's 3 rows (`fig1_label`/`fig1_value`/`fig1_status`/`fig1_pct`, …
`fig3_*`, and `perf1..3_*` for the second figure) are fully live too,
sourced from the `clients` table (denormalized ahead of time — see
`mcp_sqlite_excel/data/merge_smart_actions.py`, `data/add_case_figures.py`
and `data/add_portfolio_performance.py` — so no SQL join is needed at query
time; the generic MCP server stays schema-agnostic). `{prefix}{n}_status`
is one of `ok` / `warn` / `danger` / `-` and colors that row's value (and
bar, for cases with `figure_bars`); `{prefix}{n}_pct` (0-100) only matters
for bars.

**Adding a 7th use case:** add an entry to `cases.json` (rule code(s), tag,
icon, figure title, instructions, optionally `open_sections` /
`figure2_title`) and populate `fig1..3_*` (and `perf1..3_*` if it has a
second figure) for its clients in the Excel source, then rebuild — no
HTML/CSS edits required.

### Placeholder interpolation

Inside a list row, `{field}` is only filled when the host sets an attribute via
`data-unique-attr-*`. Use:

- `data-unique-attr-href` / `data-unique-attr-id` for links and anchors
- `data-unique-attr-data-unique-source-args` for `callTool` args
- `data-unique-attr-data-unique-payload` for `sendPrompt` payloads

A plain `data-unique-payload='…{client_name}…'` stays literal in chat.
