# Contract generation

`generate.mjs` turns a dataset's TypeSpec contract into every typed artifact the
two runtimes import. It is the mechanism behind the framework's central claim:
Python and TypeScript cannot disagree about the domain model, because neither
side writes it.

```bash
npm run generate                 # every dataset with a contract/main.tsp
npm run generate <dataset>       # just one
npm run generate:check           # regenerate, then fail if git sees a diff
```

## The pipeline

```text
datasets/<name>/contract/main.tsp
  --  tsp compile  ------------->  contract/openapi.json
  --  openapi-ts (zod plugin)  ->  astro/src/lib/generated/{zod.gen.ts,types.gen.ts,index.ts}
  --  datamodel-codegen  ------->  fastmcp/generated/models.py
```

OpenAPI 3.1 is the intermediate rather than an implementation detail: it is the
reviewable contract, and it is what lets one TypeSpec source drive two unrelated
generators. The transport is MCP, not HTTP — the HTTP-shaped operations exist
only to give those generators a stable way to understand request bodies,
response bodies, list results, and filters.

## Reproducibility

The generated files are committed and reviewed, so the script must be
deterministic. Two things make that true:

- `datamodel-codegen` runs with `--disable-timestamp`. Without it every run
  rewrites a `# timestamp:` line and the committed artifact churns on each
  regeneration, which trains reviewers to ignore diffs in generated code.
- Every output gets a fixed provenance banner naming its source `.tsp` and the
  command to regenerate it. `openapi.json` carries the same information as
  `x-generated-by` / `x-source` inside `info`, since JSON has no comments.

`npm run generate:check` regenerates everything and then runs
`git diff --exit-code -- datasets`, so CI fails on a commit whose contract and
artifacts have drifted apart.

## Failing loudly

`tsp compile` exits 0 even when its emitter wrote nothing, which would silently
leave the downstream generators reading a stale `openapi.json` and produce
plausible-looking models from an old contract. The script therefore checks that
`openapi.json` exists *and* that its mtime advanced, and aborts if either is
false.

## Toolchain versions

Reproducibility depends on the generators themselves not moving: a minor bump in
`@hey-api/openapi-ts` or the TypeSpec compiler can change generated output and
turn `generate:check` red for reasons unrelated to any contract change.

The root `package.json` declares caret ranges, so the exact versions come from
`package-lock.json`. That means CI must install with `npm ci` rather than
`npm install` — the latter is free to pick up a newer minor and produce a diff no
contract change explains.

## Adding a dataset

Create `datasets/<name>/contract/main.tsp` and a `tspconfig.yaml` emitting
OpenAPI 3.1 to `openapi.json` in the same directory. The script discovers
datasets by looking for that file, so nothing here needs editing. Output paths
are derived by convention:

| Artifact | Path |
| --- | --- |
| OpenAPI | `datasets/<name>/contract/openapi.json` |
| Pydantic | `datasets/<name>/fastmcp/generated/models.py` |
| Zod + TS | `datasets/<name>/astro/src/lib/generated/` |
