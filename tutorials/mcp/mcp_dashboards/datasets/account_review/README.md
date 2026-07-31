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
  server.py           # the MCP tools, hand-written against generated models
  deploy.sh              # Azure ACR + Web App deploy
  deploy-with-secrets.sh # wraps deploy.sh with secretspec via nix
  secretspec.toml        # secret declarations (values in 1Password)
  shell.nix / flake.nix  # ephemeral secretspec from nixpkgs
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
3. Nix + [SecretSpec](https://secretspec.dev) from nixpkgs (see below), plus
   1Password CLI (`op`) with desktop integration enabled
4. Secrets declared in [`fastmcp/secretspec.toml`](./fastmcp/secretspec.toml)
   stored in your 1Password vault (default provider URI:
   `onepassword://Private` — edit the vault name if yours differs)
5. Zitadel redirect URI (after deploy, using your `AZURE_WEBAPP_NAME`):
   `https://<AZURE_WEBAPP_NAME>.azurewebsites.net/auth/callback`

### SecretSpec via nix

From `datasets/account_review/fastmcp` — **no profile install**; ephemeral only:

```bash
cd datasets/account_review/fastmcp

# Option A — direnv (recommended)
direnv allow          # loads shell.nix → secretspec on PATH

# Option B — one-shot shell
nix-shell             # or: nix shell nixpkgs#secretspec

# Option C — flake (after `git add flake.nix shell.nix`)
nix develop
```

Keep the **system** `op` binary. Do not add `_1password-cli` from nixpkgs into
the shell — it breaks desktop CLI unlock.

Then (you run these; the agent does not touch 1Password):

```bash
# One-time: point the provider at your vault if not Private
# edit secretspec.toml → [providers].onepassword = "onepassword://YourVault"

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
./deploy-with-secrets.sh
# equivalent:
# secretspec run --profile deploy --reason "Deploy account-review MCP" -- ./deploy.sh
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

For a lab deploy without Zitadel, either omit the `ZITADEL_*` secrets or set
`AUTH_DISABLED=true` in the deploy profile.

### Redeploy

```bash
SECRETSPEC_REASON="Redeploy account-review MCP" ./deploy-with-secrets.sh
```
