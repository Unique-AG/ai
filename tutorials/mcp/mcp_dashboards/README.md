# TypeSpec MCP Dashboards

Framework for turning an Excel-backed dataset into a typed FastMCP server and
Astro dashboard.

```text
TypeSpec -> OpenAPI 3.1 -> Pydantic v2 models
                         -> Zod schemas
```

## Layout

```text
tutorials/mcp/mcp_dashboards/
  package.json              # contract generation, dev, and build entrypoints
  scripts/                  # local startup helpers
  docs/                     # architecture, dashboard build, DOM contract
  helpers/
    contracts/              # TypeSpec -> OpenAPI/Pydantic/Zod generation
    python/                 # shared FastMCP / SQLite helpers
    astro/                  # shared dashboard host (DOM engine, MCP client)
  datasets/
    account_review/         # reference dataset implementation
      contract/
      fastmcp/
      astro/
```

Each `helpers/` package has its own README covering it in depth.

## Quick start

Install dependencies once:

```bash
npm install
npm --prefix datasets/account_review/astro install
uv sync --project helpers/python
```

Start the account-review server and dashboard together:

```bash
npm run dev:account-review
```

Or run them separately:

```bash
uv run --project helpers/python python datasets/account_review/fastmcp/server.py
npm --prefix datasets/account_review/astro run dev:live-local
```

Regenerate typed artifacts after changing TypeSpec:

```bash
npm run generate                 # every dataset
npm run generate account_review  # just one
npm run generate:check           # regenerate and fail if anything was uncommitted
```

Generation is byte-stable, so `generate:check` is safe to run in CI.

Build the account-review dashboard from the repo root:

```bash
npm run build:account-review:live      # dist/live/index.html — platform artifact (zero JS)
npm run build:account-review:preview   # dist/preview/ — mock data + preview host
npm run build:account-review           # live + preview
npm run check:account-review           # test, typecheck, build, verify
```

Output lives under `datasets/account_review/astro/dist/`. The same commands exist
without the `account-review` prefix when run inside that Astro package.

## Dashboard modes

The dashboard is one static page whose data binding is expressed as
`data-unique-*` attributes, interpreted at runtime by a host:

| Mode | Host | Data |
| --- | --- | --- |
| `live` | Unique platform | Real MCP connector; the build ships zero JS |
| `preview` | `public/mock-host.js` | Local fixture, no network |
| `live-local` | `public/mcp-live-host.js` | A local FastMCP server over HTTP |

Both local hosts are bundled into `public/*.js`, which is build output — do not
edit it. Nearly all of the host is dataset-agnostic and lives in
[`helpers/astro/`](helpers/astro/README.md); a dataset's own
`astro/src/host/` holds only its schema registry and its preview-mode mirror.

The `live` build is one HTML file with no JavaScript in it, because the platform
supplies the binding engine. See
[`docs/dashboard-build.md`](docs/dashboard-build.md) for how that is achieved and
[`docs/dom-contract.md`](docs/dom-contract.md) for the contract itself.

To check the dashboard end to end:

```bash
npm run check:account-review
```

## Documentation

| Document | What it covers |
| --- | --- |
| [`docs/architecture.md`](docs/architecture.md) | The framework as a whole, the authoring workflow, and an implementation-status table recording what is built versus still aspirational |
| [`docs/dashboard-build.md`](docs/dashboard-build.md) | How the script-free `live` artifact is produced and how the dashboard stays reusable |
| [`docs/dom-contract.md`](docs/dom-contract.md) | The `data-unique-*` attribute reference |

[`docs/README.md`](docs/README.md) indexes these along with the package-level
READMEs, and suggests a reading order per task.
