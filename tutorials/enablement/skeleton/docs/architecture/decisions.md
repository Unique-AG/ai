# Decisions

## One model base

Models inherit `package_name.contract.base.Model` (`frozen`, `strict`, `extra="forbid"`). Ruff bans a raw `BaseModel` and `dataclass` outside `contract/base.py`.

## Structured concurrency

Concurrent work uses `asyncio.TaskGroup`. Ruff bans `asyncio.create_task`.

## Four checks Ruff cannot express

Keyword-only public APIs, no private imports from outside the package, no mutable module-level containers, and the budgets in `arch_budgets.toml`. `poe lint-architecture` runs them. The source of truth is `unique_toolkit.lint_architecture`. This package runs `scripts/lint_architecture.py` until it depends on `unique-toolkit`.

## Versions

Python version and dependency pins match the repo this package lives in.
