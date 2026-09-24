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
docs/                 # RM remediation processes (visual, Mermaid) — start at docs/README.md
contract/
  main.tsp            # source of truth for the public domain model
  openapi.json        # generated
fastmcp/
  data/*.xlsx         # source workbook
  data/*.sqlite       # gitignored; rebuilt from the workbook on first run
  generated/models.py # generated Pydantic models
  static/admin.html   # browser DB admin (served at `/` by the MCP process)
  admin_site.py       # REST routes for the admin UI
  import_plan.py      # workbook -> SQLite, dataset-owned
  app.py              # FastMCP entrypoint (wires runtime + tools)
  mcp_tools.py        # MCP tool handlers, hand-written against generated models
  domain.py           # domain ↔ storage mapping
  email_drafts.py     # email elicitation helpers
  runtime.py          # settings, repo, FastMCP instance
  server.py           # thin re-export shim (prefer app.py)
  deploy.sh              # Azure ACR + Web App deploy
  deploy-with-secrets.sh # wraps deploy.sh with secretspec + 1Password
  secretspec.toml        # secret declarations (values in 1Password)
astro/                   # the dashboard (see its own README)
```

## RM processes

How the six remediation use cases work (traffic-lights, statuses, sequence
diagrams) lives in [`docs/`](./docs/README.md), distilled from the
[product use-case brief](https://unique-ch.atlassian.net/wiki/spaces/Product/pages/2508980226).

## The domain

`main.tsp` models a `Client` as nested groups rather than a flat row —
`identity`, `contact`, `portfolio`, `compliance`, `review_schedule`,
`suitability`, `case_action`, and `figures` — though the source workbook is
flat, with columns like `client_name` and `hold3_status`. That
restructuring is the point: the workbook is source data, not automatically a good
API shape.

## Storage

SQLite is split by TypeSpec groups (not one wide clients row). The Excel
**Clients** sheet remains the seed; `import_plan.py` fans each row into these
tables:

```mermaid
erDiagram
  clients ||--|| contacts : client_id
  clients ||--|| portfolios : client_id
  clients ||--|| compliance : client_id
  clients ||--|| review_schedules : client_id
  clients ||--|| suitability : client_id
  clients ||--|| case_actions : client_id
  clients ||--o{ figure_metrics : client_id

  clients {
    int id PK
    text name
    text reference
    text segment
  }
  contacts {
    int client_id PK_FK
    text email
  }
  case_actions {
    int client_id PK_FK
    text status
  }
  figure_metrics {
    int id PK
    int client_id FK
    text group_name
  }
```

- `clients` — identity only (`name`, `reference`, `crd_number`, `type`, `segment`)
- 1:1 satellites — `contacts`, `portfolios`, `compliance`, `review_schedules`,
  `suitability`, `case_actions` (PK/FK `client_id`, `ON DELETE CASCADE`)
- `figure_metrics` — unrolled `fig{1..3}_*` / `hold{1..3}_*` groups

List/get tools JOIN these tables and project flat aliases (`identity_name`,
`case_action_status`, …) so the nested `Client` contract stays unchanged.
Admin edits the physical tables directly.

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
uv run --project helpers/python python datasets/account_review/fastmcp/app.py
npm --prefix datasets/account_review/astro run dev:live-local
```

Local runs default to `AUTH_DISABLED=true` (no Zitadel). The dashboard expects
the MCP on `http://127.0.0.1:8004/mcp`. Open `http://127.0.0.1:8004/` for the
DB admin console (edit rows, reset from Excel).

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

## Deploy to Azure

Uses the same pattern as [`mcp_sqlite_excel`](../../../mcp_sqlite_excel/): ACR
build + Linux Web App.

### Prerequisites

1. Azure CLI logged in (`az login`)
2. An existing Azure resource group (same as [`mcp_search`](../../../mcp_search/)
   is fine: `rg-lab-demo-001-unique-search-mcp`)
3. [SecretSpec](https://secretspec.dev) on PATH and 1Password CLI (`op`) with
   desktop integration enabled
4. Secrets declared in [`fastmcp/secretspec.toml`](./fastmcp/secretspec.toml)
   stored in your 1Password vault (default provider URI:
   `onepassword://Private` — edit the vault name if yours differs)
5. Zitadel redirect URI (after deploy, using your `AZURE_WEBAPP_NAME`):
   `https://<AZURE_WEBAPP_NAME>.azurewebsites.net/auth/callback`

### Secrets (SecretSpec + 1Password)

From `datasets/account_review/fastmcp` (agent does not touch 1Password):

```bash
cd datasets/account_review/fastmcp

# One-time: edit secretspec.toml → [providers].onepassword if vault ≠ Private
secretspec check --profile deploy

# Required Azure targets (suggested lab values):
secretspec set AZURE_SUBSCRIPTION_ID --profile deploy
secretspec set AZURE_RESOURCE_GROUP --profile deploy      # rg-lab-demo-001-unique-search-mcp
secretspec set AZURE_LOCATION --profile deploy            # swedencentral
secretspec set AZURE_WEBAPP_NAME --profile deploy         # account-review-mcp
secretspec set AZURE_CONTAINER_REGISTRY --profile deploy  # accountreviewmcpacr

# Optional Zitadel:
secretspec set ZITADEL_BASE_URL --profile deploy
secretspec set ZITADEL_CLIENT_ID --profile deploy
secretspec set ZITADEL_CLIENT_SECRET --profile deploy
```

### Deploy

```bash
cd datasets/account_review/fastmcp
az login   # once per session
./deploy-with-secrets.sh
```

What it does:

- Uses existing resource group from `AZURE_RESOURCE_GROUP` (does **not** create it)
- Builds the image in `AZURE_CONTAINER_REGISTRY`
- Creates/updates Web App `AZURE_WEBAPP_NAME` (B1 plan) in `AZURE_LOCATION`
- Sets `WEBSITES_PORT=8004`, `UNIQUE_MCP_*`, persisted
  `SQLITE_PATH=/home/data/account_review.sqlite`
- Enables Zitadel when `ZITADEL_*` credentials are present; otherwise sets
  `AUTH_DISABLED=true`
- Restarts the app

| URL | |
|-----|--|
| Admin UI | `https://<AZURE_WEBAPP_NAME>.azurewebsites.net/` |
| Status JSON | `https://<AZURE_WEBAPP_NAME>.azurewebsites.net/api/status` |
| MCP | `https://<AZURE_WEBAPP_NAME>.azurewebsites.net/mcp` |

The root URL serves a small admin console: pick a table, edit cells, delete
rows, or **Reset from Excel** to rebuild SQLite from the workbook.

### Demo data (sales)

Sales can tune the deployed demo data without running any developer tooling:

1. Open `https://<AZURE_WEBAPP_NAME>.azurewebsites.net/` (for the lab deploy:
   `https://account-review-mcp.azurewebsites.net/`).
2. Use the **Clients** tab to search for a client, edit cells, and click
   **Save** on the changed row.
3. Wait for the dashboard's next poll (about 15 seconds), or refresh the
   dashboard iframe if you need to see the change immediately.
4. Use **Reset from Excel...** when the demo should go back to the clean seed
   data. This wipes ad-hoc edits and rebuilds SQLite from the workbook packaged
   in the deployed image.

The lab admin URL is a shared demo surface. Do not enter production client data
or production secrets.

For a lab deploy without Zitadel, either omit the `ZITADEL_*` secrets or set
`AUTH_DISABLED=true` in the deploy profile.

### Redeploy

```bash
SECRETSPEC_REASON="Redeploy account-review MCP" ./deploy-with-secrets.sh
```
