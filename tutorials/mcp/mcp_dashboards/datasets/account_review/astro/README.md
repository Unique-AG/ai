# Account Review Dashboard

Typed Astro dashboard for the `account_review` dataset. It consumes nested
`Client` objects from the typed FastMCP server and renders the same
`data-unique-*` markup in three modes:

| Mode | From repo root | From this folder | Data source |
| --- | --- | --- | --- |
| Live | `npm run build:account-review:live` | `npm run build:live` | Platform host binds live; the build ships zero JS |
| Preview | `npm run build:account-review:preview` | `npm run build:preview` | Generated `src/data/mock.json`, via the `mock-host` bundle |
| Live local | — | `npm run dev:live-local` | Real MCP server, via the `mcp-live-host` bundle |

## Host scripts

Both hosts are bundled from `src/host/` into `public/` by
`scripts/build-hosts.mjs` (wired into the `dev` and `build` scripts, or run
directly with `npm run hosts`). `public/*.js` is build output and gitignored —
edit the TypeScript instead.

Most of the host is not in this app. The `data-unique-*` interpreter, the MCP
client, the elicitation form, and the entire `live-local` host live in
[`helpers/astro/host/`](../../../helpers/astro/README.md) and are imported here as
`@mcp-dashboards/host/*`. What remains under `src/host/` is only what is specific
to account_review:

- `liveHost.ts` — a few lines registering this dataset's generated Zod schemas
  against its tool names. That validation means a drift between the Python and
  TypeScript sides of the contract surfaces on the page instead of as a blank
  panel.
- `mockHost.ts` — a client-side mirror of this dataset's list / count / update
  tools, for preview mode.

See [`docs/dom-contract.md`](../../../docs/dom-contract.md) for the contract
itself, and [`docs/dashboard-build.md`](../../../docs/dashboard-build.md) for
how the `live` build stays script-free.

## Quick start

From `tutorials/mcp/mcp_dashboards/`:

```bash
npm run dev:account-review
```

Or run the pieces separately:

```bash
# Terminal 1
uv run --project helpers/python python datasets/account_review/fastmcp/server.py

# Terminal 2, from this folder
npm run dev:live-local
```

## Useful commands

From the `mcp_dashboards` root, prefer the project-prefixed scripts
(`npm run build:account-review:live`, `npm run check:account-review`, …). From
this folder:

```bash
npm install
npm run mock:data      # regenerate src/data/mock.json from the typed server
npm run hosts          # rebuild public/*.js from src/host/
npm run test
npm run typecheck
npm run build
npm run verify         # jsdom smoke test for preview mode
npm run check          # test + typecheck + build + verify
npm run screenshot     # refresh screenshots/console.png and screenshots/client.png
```

Architecture and framework conventions live in
[`docs/architecture.md`](../../../docs/architecture.md).
