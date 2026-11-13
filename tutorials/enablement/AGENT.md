# Agent instructions — new Python work

Read this file before you create or extend Python code. Ask which kind the user is starting. One branch wins.

- MCP
- API
- Tool
- Library. A postprocessor is a library.
- Feature

A package is a new installable project. A feature is behaviour inside a package that already exists.

References live in `tutorials/enablement/references/`. Read a reference only when this file names it.

## New package

Copy `tutorials/enablement/skeleton/` into the directory the user names. If they did not name one, ask. Do not copy `.venv`, `.pytest_cache`, `.ruff_cache`, `.import_linter_cache`, or `uv.lock`.

The skeleton uses `src/<package>/` because `pyproject.toml` sets `module-root = "src"`. Rename the directories `src/package_name` and `tests/package_name`. Replace every `package_name` and `package-name` in the copied files.

Match the Python version and the pin style of the repo the package lands in. Connectors packages use Python 3.14 and exact pins. Packages in the ai workspace use open ranges and that repo's floor. Change `requires-python`, the Ruff `target-version`, and the basedpyright `pythonVersion` to that floor. Do not invent a third style. Record dependency choices in `docs/architecture/decisions.md`.

If the package depends on `unique-toolkit`, delete `scripts/lint_architecture.py` and point `lint-architecture` at `python -m unique_toolkit.lint_architecture --package <name>`. `unique-mcp` depends on `unique-toolkit`, so an MCP that depends on `unique-mcp` takes this path. Otherwise keep the script. The toolkit module is the source of truth. The script is a copy of it.

Ask the user to `@` the copied files, then read them as the rules for the rest of the task:

- `AGENTS.md`
- `docs/architecture/layers.md`
- `docs/architecture/import-rules.md`
- `docs/architecture/decisions.md`

## MCP

Read `references/mcp.md`. Depend on FastMCP and `unique-mcp`. Depend on `unique-sdk` only when the server calls the SDK. Call `configure_tracing` only when the server exports traces.

## API

Read `references/api.md`. Depend on FastAPI. Do not call `unique_mcp`'s logger. Depend on `unique-toolkit` when this API records metrics or exports traces.

## Tool

Read `references/service.md`. Delete `src/<package>/app.py`. No server library. Depend on `unique-toolkit` when the tool calls Unique.

## Library

Read `references/service.md`. Delete `src/<package>/app.py`. The package is imported. It does not run a process. A postprocessor takes this branch. Depend on `unique-toolkit` when the library calls Unique. The lint command then follows the new-package rule above.

## Feature

Do not copy the skeleton. Read `references/feature.md`. Use the layout the package already has.

If the package has an `AGENTS.md`, paste the note from that reference into it. If it has none, add code and tests in the modules and style that package already uses. Do not add `AGENTS.md`, a `pyproject.toml`, `arch_budgets.toml`, a layers document, `contract`, or the four checks.

Add code and tests beside the existing code. Add an import-linter row only when the package already uses import-linter and the feature adds an allowed edge.

## Practices

When the work is tests, a failure path, a docstring, dependencies, a commit, or a pull request, read `references/practices.md`. Read only the skill that matches. Ask the user before you apply a practice the copied rules do not already require.

## Logs, metrics, traces

- MCP logs, health, and Prometheus: `unique_mcp`, as `references/mcp.md` says.
- Other Python metrics: `unique_toolkit.monitoring` and the `monitoring` extra.
- Traces: `unique_toolkit.monitoring.configure_tracing` and the `otel` extra, only when the process should export them.
- Do not invent a JSON log format for non-MCP Python. `unique_toolkit.app.init_logging` is not that format.
