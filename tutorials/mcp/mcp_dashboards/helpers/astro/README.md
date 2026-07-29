# Shared dashboard host

Dataset-agnostic browser code for `mcp_dashboards` dashboards. This is the
counterpart to `helpers/python/`: reusable machinery that every dataset's Astro
app consumes, rather than anything specific to one dataset.

Datasets import it through the `@mcp-dashboards/host/*` alias, declared in each
app's `tsconfig.json`. esbuild reads that alias straight from the tsconfig, so
`scripts/build-hosts.mjs` needs no extra configuration.

```ts
import { startLiveHost } from "@mcp-dashboards/host/liveHost.ts";
import { renderRows } from "@mcp-dashboards/host/dom.ts";
```

## Modules

| Module | What it is |
| --- | --- |
| `dom.ts` | The `data-unique-*` interpreter: path reads, interpolation, attribute bindings, keyed row reconciliation, state placeholders, action delegation, polling |
| `binding.ts` | Row enrichment for local hosts — dotted-path mirrors and precomputed attr helpers (`client_href`, tooltips, bar styles) |
| `mcpClient.ts` | MCP over Streamable HTTP (JSON-RPC 2.0), including SSE framing and elicitation round-trips |
| `elicitForm.ts` | Renders an MCP elicitation request as a modal form, built from the requested JSON Schema |
| `liveHost.ts` | The whole `live-local` host, parameterised by a per-dataset tool-response schema registry |

None of these reference a domain model, a tool name, or a table. Everything they
do is driven by the attributes on the page — see
[`docs/dom-contract.md`](../../docs/dom-contract.md).

These hosts exist only for local development. The `live` build ships no host at
all, because the Unique platform provides the binding engine; see
[`docs/dashboard-build.md`](../../docs/dashboard-build.md).

## No npm dependencies

This package imports nothing from npm, deliberately. `liveHost.ts` describes a
generated schema structurally rather than importing zod:

```ts
export interface ToolResultSchema {
  parse(payload: unknown): unknown;
}
```

That keeps the shared host installable anywhere, and avoids the failure mode
where a dataset app and this package resolve two different copies of zod and
`err instanceof ZodError` silently stops matching. Validation errors are detected
structurally, by looking for an `issues` array.

## What stays in a dataset

Two things, both small:

- **The tool-response schema registry.** Each dataset's
  `src/host/liveHost.ts` is a few lines: import the generated schemas, map them
  to tool names, call `startLiveHost`.
- **The preview host.** `src/host/mockHost.ts` is a client-side mirror of that
  dataset's list / count / update tools, so it cannot be shared. It is ~95 lines
  and does no DOM work of its own — that all comes from `dom.ts`.

## Adding a dataset

1. Copy the dataset's `tsconfig.json` `paths` entry, adjusting the depth of the
   relative path to `helpers/astro/host/*`.
2. Write `src/host/liveHost.ts` registering the dataset's generated schemas.
3. Write `src/host/mockHost.ts` mirroring the dataset's tools for preview mode.
4. Point `scripts/build-hosts.mjs` at both entries.
