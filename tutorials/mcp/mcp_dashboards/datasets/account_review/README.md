# account_review

The reference dataset. An account-review console for a relationship manager: a
portfolio of clients, each with compliance status, risk level, review scheduling,
suitability, and a set of dashboard figures.

It exists to be copied. Every framework decision documented in
[`docs/architecture.md`](../../docs/architecture.md) is demonstrated here, and it
is currently the only consumer of the shared helpers — so it is also the thing
that defines what "shared" means in practice.

## Layout

```text
contract/
  main.tsp            # source of truth for the public domain model
  openapi.json        # generated
fastmcp/
  data/*.xlsx         # source workbook
  data/*.sqlite       # gitignored; rebuilt from the workbook on first run
  generated/models.py # generated Pydantic models
  import_plan.py      # workbook -> SQLite, dataset-owned
  server.py           # the MCP tools, hand-written against generated models
astro/                # the dashboard (see its own README)
```

## The domain

`main.tsp` models a `Client` as nested groups rather than a flat row —
`identity`, `contact`, `portfolio`, `compliance`, `review_schedule`,
`suitability`, `case_action`, and `figures` — though the source workbook is
flat, with columns like `client_name` and `hold3_status`. That
restructuring is the point: the workbook is source data, not automatically a good
API shape.

## Storage

Two tables, designed from the TypeSpec model rather than from the spreadsheet:

- `clients`, with domain-prefixed columns (`identity_name`, `case_action_status`)
  so the server's mapping from storage row to domain model stays mechanical.
- `figure_metrics`, normalising the workbook's repeated `fig{1..3}_*` column
  groups into rows, with a cascading foreign key to `clients`.

`import_plan.py` inserts clients one at a time so it can read back each
`lastrowid` and attach figure rows to the key SQLite actually assigned, rather
than assuming workbook order matches the generated ids.

## Tools

| Tool | Purpose |
| --- | --- |
| `list_clients` | Filtered, sorted, paginated clients. Loads all figures for a page in one batched query |
| `count_clients_by` | Grouped counts, with the column constrained to a `Literal` so only real columns are reachable |
| `update_client` | Applies a `ClientUpdate`, raising on any field with no storage column |
| `list_schema` | Describes the live SQLite schema |
| `reset_from_excel` | Rebuilds the database from the workbook |

## Running it

From the `mcp_dashboards` root:

```bash
npm run dev:account-review     # server + live-local dashboard together

# or separately
uv run --project helpers/python python datasets/account_review/fastmcp/server.py
npm --prefix datasets/account_review/astro run dev:live-local
```

Regenerate typed artifacts after editing `contract/main.tsp`:

```bash
npm run generate account_review
```

Build the dashboard (from the `mcp_dashboards` root):

```bash
npm run build:account-review:live      # platform artifact → astro/dist/live/index.html
npm run build:account-review:preview
npm run build:account-review
npm run check:account-review
```
