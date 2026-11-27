# Enablement

Pick one kind, then tell your agent to read `tutorials/enablement/AGENT.md`.

- **MCP** — a new package that runs a FastMCP server
- **API** — a new package that runs a FastAPI server
- **Tool** — a new package with no server
- **Library** — a new package other code imports. A postprocessor is a library
- **Feature** — behaviour inside a package that already exists

A package is the installable project. It has its own `pyproject.toml`. A feature is not a new package.

Give the agent the path to `AGENT.md`. Do not `@` that file.

After a new package is copied, `@` these files in the project. They are the rules for the rest of the work:

- `AGENTS.md`
- `docs/architecture/layers.md`
- `docs/architecture/import-rules.md`
- `docs/architecture/decisions.md`

A feature does not copy the skeleton. `@` those files only when the package already has them.

`tutorials/enablement/references/` holds short examples. The agent reads one when `AGENT.md` names it. It does not copy that folder into the project.

```
tutorials/enablement/
  README.md
  AGENT.md
  references/          # read on request: mcp, api, service, adapter, facade, feature, practices
  skeleton/            # copy this for a new package
    pyproject.toml
    arch_budgets.toml
    AGENTS.md
    scripts/lint_architecture.py
    docs/architecture/
    src/package_name/  # src layout because module-root = "src"
      app.py           # composition root; a tool or library deletes it
      contract/
    tests/package_name/contract/
```

`package_name` is a placeholder. The skeleton uses `src/<package>/`. A feature uses the layout the existing package already has.
