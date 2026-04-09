---
name: python-ruff-after-edit
description: >-
  Runs Ruff to auto-fix lint (including import sorting) and format Python files
  after edits. Use after creating or modifying any .py file in this repository,
  before finishing a task that touched Python, or when the user asks to lint,
  format, or fix imports for Python changes.
---

# Python: Ruff after edit

## When to apply

- **Always** run the commands below after you edit, add, or move `.py` files in this repository (e.g. `unique_toolkit/`, `unique_sdk/`, `tool_packages/*`, `connectors/*`, `postprocessors/*`, `tutorials/**`).
- Run again if follow-up edits introduce new lint or format drift.
- If the user only asked a question and no files changed, skip.

## Resolve working directory

This repository contains **multiple independent Python packages** (each with its own `pyproject.toml` and often its own `uv.lock`). Ruff must run with the config and environment of the package that owns the file.

1. For each edited `.py` path, walk **up** from the file’s directory to the first directory that contains a `pyproject.toml` or `ruff.toml`. Use that directory as **package root** for that file.
2. If several edited files map to different package roots, run Ruff **once per distinct package root**, passing only the paths that belong to that root (relative or absolute).

## Commands (lint + imports + format)

From **package root**, run **both** in this order:

```bash
ruff check --fix <paths...>
ruff format <paths...>
```

Replace `<paths...>` with the edited file(s). To fix the whole package after a broad change, use `.` instead of explicit paths.

### How to invoke `ruff`

Use the project’s toolchain when present:

| Signal | Invocation |
|--------|------------|
| `uv.lock` in package root | `uv run ruff check --fix …` and `uv run ruff format …` |
| `poetry.lock` in package root | `poetry run ruff check --fix …` and `poetry run ruff format …` |
| Neither | `ruff` on `PATH` (ensure it is installed) |

If a command is missing, sync dev dependencies for that package (e.g. `uv sync --group dev` or equivalent) and retry.

## What this covers

- **`ruff check --fix`**: fixable rules only, including **import sorting** when enabled in that package’s config.
- **`ruff format`**: Black-compatible formatting (run both; format after check).

## If Ruff fails

- Read the remaining diagnostics; fix manually or adjust only that package’s `[tool.ruff]` / `ruff.toml` if the rule is intentionally excluded there.
- Do not silence new violations globally unless the user asks.

## Optional cross-check

If the package defines a lint script or CI documents a specific Ruff invocation, align with that after the steps above when the user expects CI parity.
