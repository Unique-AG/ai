# The `data-unique-*` DOM Contract

A dashboard built here ships as a single static HTML page with no JavaScript of
its own. Data binding and actions are expressed as `data-unique-*` attributes,
which a **host** interprets at runtime.

This is what makes the page portable: the same markup is driven by the Unique
platform's binding engine in production and by a small local host during
development, with no build-time branching in the components.

For how that page is produced — how Astro is held to a script-free build, and
what stops a stray bundle getting into it — see
[dashboard-build.md](./dashboard-build.md).

## The three hosts

| Mode | Host | Data source | Ships JS |
| --- | --- | --- | --- |
| `live` | The Unique platform | Real MCP connector | No — `dist/live/` is one HTML file |
| `preview` | `public/mock-host.js` | `window.__MOCK_DATA__` from `src/data/mock.json` | Yes |
| `live-local` | `public/mcp-live-host.js` | A local FastMCP server over Streamable HTTP | Yes |

Both local hosts are bundled from a dataset's `src/host/` by
`scripts/build-hosts.mjs`, which writes only the host that the mode being built
actually loads. `live` gets an empty `public/`, so its artifact cannot
accidentally carry a script.

Everything documented below is implemented once, in
`helpers/astro/host/dom.ts`, and shared by every dataset via the
`@mcp-dashboards/host/*` alias. The two hosts differ only in where rows come
from: the `live-local` host is shared too (`helpers/astro/host/liveHost.ts`) and
a dataset only registers its generated schemas with it, while `mockHost.ts` stays
per-dataset because it mirrors that dataset's own tools. See
[`helpers/astro/README.md`](../helpers/astro/README.md).

## Attributes

### Declaring a list

Put these on the container element. `dataListAttrs()` in `src/lib/contract.ts`
emits them, so call sites do not hand-write attribute names.

| Attribute | Meaning |
| --- | --- |
| `data-unique-list` | Identifies the list. Referenced by `data-unique-source-refresh`. |
| `data-unique-source-server` | MCP server id to call (`config.mcp_server`). |
| `data-unique-source-tool` | Tool name, e.g. `list_clients`. |
| `data-unique-source-args` | JSON tool arguments. |
| `data-unique-source-path` | Dotted path to the row array inside the result, defaulting to `rows`. |
| `data-unique-source-poll` | Re-hydrate interval in ms (`config.poll_ms`). Honoured by the live-local host; the preview host ignores it, because local fixture data only changes on click. |

### Rendering rows

The container holds one `<template data-unique-item>`. It is cloned per row.

| Attribute | Meaning |
| --- | --- |
| `data-unique-field="path"` | Sets the element's text to the row value at `path`. |
| `data-unique-key="path"` | Marks the row-identity field. Required — see below. |
| `data-unique-attr-X="..."` | Sets attribute `X` on the element (see below). |

A row template must have **exactly one root element**, because a row's identity is
that element's identity. The host tags each rendered root with `data-unique-row`
and records its key in `data-unique-row-key`.

### Rows are reconciled, not replaced

On every re-hydration — a poll, or a refresh after a mutation — rows are matched
against what is already rendered by their `data-unique-key` value. A row that is
still present keeps its existing element and is rebound in place; only new rows
are created, only departed rows are removed, and nothing moves unless the order
actually changed. Rebinding is safe to repeat because `data-unique-field` and
`data-unique-attr-*` are read, never consumed.

This is not only about avoiding flicker. The client detail page is routed by CSS
`:target`, so it stays open only while the browser's target element is the
`<main id="client-N">` that a row rendered. A browser resolves the target element
at navigation time and does not re-resolve it when a *new* element with the same
id appears, so destroying and recreating that element leaves `:target` matching
nothing and silently returns the reader to the console view. Preserving element
identity is what keeps an open page open, along with its scroll position and any
focus inside it.

A template with no `data-unique-key` cannot be reconciled and falls back to
replacing every row, which will break `:target` routing and reset scroll. Give
every row template a key.

### `data-unique-attr-*` resolution

The value is interpreted one of two ways:

- **Contains `{...}`** — treated as a template, and every `{dotted.path}` is
  replaced with the row's value.
- **No braces** — the whole value is a single field name, and the row's value at
  that path is copied in.

The indirection exists so the browser never acts on an un-interpolated value. An
`href` written directly as `href="/client/{id}"` would be a real link to a
literal `{id}` before any host ran; written as
`data-unique-attr-href="/client/{id}"` it only becomes an `href` once a row is
bound. The same applies to JSON tool arguments, whose own `{`/`}` characters sit
next to the placeholder braces — which is why `contract.ts` types `argsTemplate`
as a plain `string` while `attrTemplate` and `sendPromptAttrs` check every
placeholder against the row type.

### Empty, loading, and error states

Sibling elements carrying `data-unique-state="loading|ok|empty|error"` are shown
or hidden as a unit: after hydration exactly the one matching the current state is
visible. A failed tool call puts its message into the `error` element, so a
contract violation or an unreachable server is visible on the page and not only in
the console.

### Actions

| Attribute | Meaning |
| --- | --- |
| `data-unique-action="callTool"` | Click calls `data-unique-source-tool` with `data-unique-source-args`. |
| `data-unique-action="sendPrompt"` | Click hands `data-unique-payload`'s `prompt` to the host. |
| `data-unique-source-refresh` | Comma-separated `data-unique-list` ids to re-hydrate after a successful call. |

Clicks are handled by one delegated listener on `document`, so rows added by a
later hydration need no rebinding.

`sendPrompt` is the platform's "ask the assistant about this row" handoff. Locally
there is no assistant, so both hosts render the interpolated prompt into the
`#mock-prompt-preview` element instead — enough to catch an un-interpolated
placeholder, which is the bug this path has actually had.

## Response validation

The live-local host validates each tool result against the Zod schema generated
from the same TypeSpec contract the server generates its Pydantic models from:

```ts
const TOOL_RESULT_SCHEMAS = {
  list_clients: zClientListResult,
  count_clients_by: zCountByResult,
  update_client: zClient,
};
```

A tool with no registered schema passes through unvalidated. A registered tool
whose payload does not match raises, and the message lands in the list's `error`
state. This is deliberate: a drift between the Python and TypeScript sides of one
contract should be loud, because its quiet failure mode is a panel that renders
blank for a reason nobody can see.

The preview fixture is validated once at build time in `src/lib/mode.ts`, so the
preview host does not re-check it and does not bundle Zod.

## Platform row shape vs live-local

The [Unique platform iframe host](https://unique-ch.atlassian.net/wiki/spaces/Product/pages/2368569406/Iframe+communication+framework)
and the local `live-local` host read the same `data-unique-field` attributes,
but they resolve row values differently:

| Host | `data-unique-field="identity.name"` resolves as |
| --- | --- |
| **Platform** | `item["identity.name"]` — a single flat key on the row object |
| **live-local** (`dom.ts`) | `item.identity.name` — dotted-path traversal via `readPath()` |

A TypeSpec domain model is nested (`Client.identity.name`). If a list tool returns
only that nested JSON, the platform clones rows but leaves every cell empty — the
symptom looks like “data arrived, nothing rendered”.

Dataset list tools therefore return **both shapes** in each row:

- the nested domain object (for `live-local`, which still validates against the
  generated Zod schema), and
- dotted-path mirror keys (`"identity.name"`, `"case_action.status"`, …) plus a
  few precomputed attribute helpers the platform cannot derive from `{field}`
  templates (`client_href`, `client_dom_id`, `figures.mandate.0.pct_bar_style`,
  …).

That enrichment lives in `helpers/python/src/mcp_dashboards/binding.py` and is
applied in each dataset's `server.py` when building list / update responses (see
`account_review`'s `_client_binding_rows()`).

When adding a new bound field or attribute:

1. Keep the nested domain path in Astro (`clientRow.field("identity.name")`) — it
   matches TypeSpec and works in `live-local`.
2. Ensure the server adds the matching dotted mirror key (automatic when using
   `enrich_binding_row()`).
3. Prefer `clientRow.attr("href", "client_href")` over
   `attrTemplate("href", "#client-{id}")` for platform attrs — the bridge does
   not interpolate `{field}` templates; precompute the value on the row instead.

Also set `config.json`'s `mcp_server` to the connector id registered in Unique
before building `dist/live/` — `data-unique-source-server` is baked in at build
time and must match the platform connector exactly.

## Adding a bound list

1. Add or extend the tool in the dataset's `main.tsp`, then
   `npm run generate <dataset>`.
2. Implement the tool in `fastmcp/server.py` against the regenerated models.
3. Bind the container with `dataListAttrs({ listName, tool, args })` and bind
   fields inside the `<template>` with `clientRow.field(...)` / `.attr(...)`.
4. Register the tool's response schema in `src/host/liveHost.ts` so live payloads
   are validated.
5. Verify all three modes: `npm run check` covers preview end to end;
   `npm run dev:live-local` with the server running covers the live path.
