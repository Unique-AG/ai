# The dashboard build

How Astro produces a script-free HTML page, and how the same source produces two
other artifacts that are fully interactive.

This is the build-time companion to [`dom-contract.md`](./dom-contract.md), which
describes the runtime contract those artifacts express.

## Why script-free

The `live` artifact is embedded in the Unique platform, and the platform supplies
its own `data-unique-*` engine. A dashboard that shipped its own JavaScript would
be running a second, competing interpreter over the same attributes.

So the deliverable is one HTML file with no behaviour in it at all — only markup
that *describes* which tool feeds which element. Today that is literally true:

```text
dist/live/
  index.html      79 KB, 0 <script> tags, 0 external stylesheets
```

## How Astro is held to that

Astro will happily emit JavaScript. Four things keep it from doing so here, and
all four have to hold — losing any one of them silently reintroduces a bundle.

**No client islands.** Nothing in `src/` uses `client:load`, `client:visible` or
any other hydration directive, and no component ships a non-inline `<script>`.
With no island to hydrate, Astro's build emits no client bundle and no
`_astro/` directory. This is the load-bearing one, and it is why interactivity
has to be expressed as attributes rather than as components: the DOM contract
exists precisely so that behaviour can live outside the artifact.

**Static output.** `output: "static"` with a single page in `src/pages/`, so
there is no server runtime or router to ship.

**Inlined CSS.** `build.inlineStylesheets: "always"` in `astro.config.mjs`, plus
`<style is:global set:html={baseCss}>` in `index.astro`. Without this Astro emits
a `_astro/*.css` file and a `<link rel="stylesheet">`, which would make the
artifact a directory rather than a file. Styling is a real part of the contract
here, because the dashboard routes with CSS `:target` instead of a script.

**A per-mode `public/`.** This is the subtle one. Astro copies everything in
`public/` into every `outDir` verbatim, without compiling it — so a stray
`public/mock-host.js` left over from a previous `npm run build:preview` would be
copied into `dist/live/` and quietly break the zero-JS guarantee, even though
nothing references it. `scripts/build-hosts.mjs` therefore takes the target mode
as an argument and deletes any host bundle that mode does not use before
building. `build:live` runs it with `live`, which writes nothing and clears
everything:

```json
"build:live": "node scripts/build-hosts.mjs live && DASHBOARD_MODE=live astro build --outDir dist/live"
```

## One source, three artifacts

`DASHBOARD_MODE` selects the mode at build time; `src/lib/mode.ts` reads it.

| Mode | Command | Host | Data |
| --- | --- | --- | --- |
| `live` | `npm run build:live` | The platform's engine | Real MCP connector |
| `preview` | `npm run build:preview` | `public/mock-host.js` | `src/data/mock.json`, no network |
| `live-local` | `npm run dev:live-local` | `public/mcp-live-host.js` | A local FastMCP server over HTTP |

The important property is that **the markup does not vary between them**.
Comparing the built files, all three emit the same 254 `data-unique-*`
attributes, and the only differences between `dist/live/index.html` and
`dist/live-local/index.html` are:

- the `<script>` tags themselves,
- a hidden `<pre id="mock-prompt-preview">` the local hosts use to show what a
  `sendPrompt` action would send,
- the mode banner, which is deliberately loud so a non-platform build is never
  mistaken for the real artifact.

Everything else is byte-identical. That is what makes `preview` and `live-local`
trustworthy: they exercise the same bindings the platform will, so a binding that
works locally is not a different binding from the one that ships.

All three come from one component, which is the only place the modes diverge:

```21:33:datasets/account_review/astro/src/components/HostScripts.astro
{(mode === "preview" || mode === "live-local") && <pre id="mock-prompt-preview" hidden></pre>}
{mode === "preview" && (
  <script is:inline define:vars={{ mockData }}>
    window.__MOCK_DATA__ = mockData;
  </script>
)}
{mode === "preview" && <script is:inline src="/mock-host.js"></script>}
```

`is:inline` is required rather than stylistic: `define:vars` only works on inline
scripts, and dropping it would let Astro process the tag and emit a bundle. It is
also why each host reads its input off `window` instead of receiving arguments.

## What Astro is actually doing

Used this way Astro is a compile-time template engine, not a client framework.
Components, props, imports and typed helpers all evaporate at build; what is left
is HTML and attributes.

That is the whole point. It buys the authoring ergonomics of components —
`<DataList>`, `<ClientDetailPage>`, typed field helpers — with none of the runtime
cost, and it keeps the artifact something the platform can host without knowing
anything about how it was produced.

## How this stays reusable

Reuse is layered, and each layer removes a different kind of duplication.

**The markup encodes bindings, not data.** A component never renders a client; it
renders a template plus the attributes describing where clients come from. So the
same page works against mock data, a local server, or the platform, and adding a
dataset means new bindings rather than a new rendering strategy.

**Attribute sets live in components.** Every bound list needs the same five
`data-unique-source-*` attributes. `DataList.astro` emits them from one helper,
so a tool or argument name cannot drift between two lists that should agree.

**Attribute values are type-checked.** `src/lib/contract.ts` derives its field
helpers from the generated Zod schemas, so `clientRow.field("clint_name")` is a
compile error rather than a silently empty binding at render time. Templates like
`href="#client-{id}"` are checked the same way, with each `{placeholder}` resolved
against the row type.

**The interpreter is shared.** Everything that reads those attributes at runtime
lives in `helpers/astro/host/` and is imported by every dataset as
`@mcp-dashboards/host/*`. See [`../helpers/astro/README.md`](../helpers/astro/README.md).

**Only two files per dataset are hand-written host code.** A dataset writes
`src/host/liveHost.ts` (registering its generated schemas) and
`src/host/mockHost.ts` (mirroring its own tools for preview). Nothing else.

## Checking the guarantee

The zero-JS property is currently verified by inspection rather than enforced by
the build:

```bash
npm run build:account-review:live
find datasets/account_review/astro/dist/live -name "*.js" | wc -l    # must be 0
rg -c "<script" datasets/account_review/astro/dist/live/index.html   # must be 0
```

`npm run check:account-review` runs the unit tests, `astro check`, all builds, and
`scripts/verify-preview.mjs`, which executes the preview bundle in a DOM and
asserts the bindings actually hydrate. It does not yet assert that `dist/live`
is script-free — worth adding, since that invariant is the reason the artifact is
acceptable to the platform at all.
