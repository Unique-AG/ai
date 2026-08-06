---
name: excel-mcp-dashboard
description: Build TypeSpec-driven Excel dashboard datasets. Use when creating a typed FastMCP app and Astro dashboard from an Excel workbook, adding a new mcp_dashboards dataset, or regenerating Pydantic and Zod models from TypeSpec/OpenAPI.
---

# Excel MCP Dashboard

## Dataset Layout

Create one folder per dataset:

```text
datasets/<dataset>/
  contract/    # TypeSpec source and generated OpenAPI
  fastmcp/     # Excel, SQLite, generated Pydantic models, import_plan.py, server.py
  astro/       # generated Zod schemas, Astro dashboard app, src/host/ dataset host entries
```

Reusable helpers live under:

```text
helpers/python/     # mcp_dashboards Python package
helpers/contracts/  # generation script
helpers/astro/      # dataset-agnostic dashboard host, imported as @mcp-dashboards/host/*
```

Use `datasets/account_review/` as the reference implementation for a new dataset.

## Workflow

1. Inspect the Excel workbook and classify sheets as resources, lookups, summaries, or documentation.
2. Propose a better TypeSpec domain model before coding. Do not blindly mirror raw spreadsheet columns if grouping, naming, create/update/filter variants, or nested concepts would produce a clearer API/dashboard contract.
3. Decide the SQLite storage mode. Prefer TypeSpec-aligned curated storage, whose column names are the domain paths with dots replaced by underscores (`identity.name` -> `identity_name`); write an Excel import plan that translates workbook sheets/columns into that schema. Expect the server to still map flat rows onto the nested contract — see `docs/architecture.md#domain-to-storage-mapping`.
4. Author `datasets/<dataset>/contract/main.tsp`. Use snake_case for the first pass when it avoids alias churn, but prefer a curated domain model when the workbook shape is messy.
5. Emit OpenAPI 3.1 with `datasets/<dataset>/contract/tspconfig.yaml`.
6. Generate committed artifacts (byte-stable; `npm run generate:check` fails if a commit is missing a regeneration):

```bash
npm run generate <dataset>
```

This produces:

```text
datasets/<dataset>/contract/openapi.json
datasets/<dataset>/fastmcp/generated/models.py
datasets/<dataset>/astro/src/lib/generated/zod.gen.ts
datasets/<dataset>/astro/src/lib/generated/types.gen.ts
```

7. Implement `datasets/<dataset>/fastmcp/server.py` by passing dataset-local paths into `AppSettings`:

```python
settings = AppSettings(
    excel_path=DATASET_ROOT / "data" / "<dataset>.xlsx",
    sqlite_path=DATASET_ROOT / "data" / "<dataset>.sqlite",
)
```

8. Write the typed tools by hand against the generated Pydantic models. There is no generic CRUD registrar to inherit from, on purpose. Follow the reference server's conventions:
   - Declare tools `def`, not `async def`, so FastMCP runs their blocking SQLite work in a worker thread.
   - Wrap each one in `@tool_errors(logger)` from `mcp_dashboards.tools`, and annotate only the domain model as the return type — failures are raised as `ToolError`, never returned as a success payload.
   - Bound every pagination argument with `Annotated[int, Field(ge=..., le=...)]` and constrain group-by / enum arguments with `Literal`, so FastMCP rejects bad input before the handler runs.
   - Read children for a page of parents with `repo.list_rows_where_in(...)` rather than one query per row.
   - Raise on an unmapped update field instead of silently dropping it.
9. Copy or adapt `datasets/account_review/astro` into `datasets/<dataset>/astro` and re-export generated Zod schemas from `src/lib/schema.ts`. Do not copy the host itself: `dom.ts`, `mcpClient.ts`, `elicitForm.ts` and the `live-local` host are shared from `helpers/astro/host/`, reached through the `@mcp-dashboards/host/*` alias in `tsconfig.json` (adjust the relative path, and keep `helpers/astro/host/**/*` in `include` so it gets type-checked). Write only two files under `src/host/`: a `liveHost.ts` that registers this dataset's generated schemas and calls `startLiveHost`, and a `mockHost.ts` mirroring this dataset's tools for preview mode. Never hand-write `astro/public/*.js`; those are esbuild output.
10. Validate the Python helper package with `uv run pytest` from `helpers/python`, and the dashboard with `npm run check` in the dataset's astro app.

## Rules

- Do not hand-edit generated files except when documenting a blocked codegen step. This includes `openapi.json`, `models.py`, `zod.gen.ts`, `types.gen.ts`, and `astro/public/*.js`.
- Write down the model-design decision before generating code.
- Keep each dataset's SQLite DB under `datasets/<dataset>/fastmcp/data/`.
- Prefer TypeSpec-aligned SQLite tables and an explicit Excel import plan, so the server's remaining mapping is mechanical.
- Prefer OpenAPI 3.1 as the shared generation boundary.
- Preserve the `data-unique-*` DOM contract in Astro components; see `docs/dom-contract.md` for the attribute reference.
- Keep the `live` build script-free: no `client:*` directives, no `<script>` without `is:inline`, no npm imports in browser code, and never add a file to `astro/public/` by hand. The platform supplies the binding engine, so express interactivity as `data-unique-*` attributes instead. After building, `find dist/live -name "*.js"` must return nothing. See `docs/dashboard-build.md`.
