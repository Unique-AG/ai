# Rules for this package

These rules apply to this package.

## Where new work goes

New behaviour goes in a layer that already exists, or in a new layer recorded in `docs/architecture/layers.md` and `docs/architecture/import-rules.md` in the same change. `contract` imports nothing else in this package.

A feature inside this package adds code, tests beside it, a short note in this file, and an import-linter row when it adds an allowed edge. It does not add a new project.

When you add a service class, an adapter, or a facade, read the matching file in the ai repo at `tutorials/enablement/references/`.

When the work is tests, a failure path, a docstring, dependencies, a commit, or a pull request, read `tutorials/enablement/references/practices.md` there. Ask before you apply a practice this file does not already require.

## Public functions

Every public function and method takes keyword arguments only. A positional signature is allowed only for an interface this package does not own. Mark it on the same line or the line above:

```python
# arch-allow-positional: the framework passes the value
def handle(event: object) -> None: ...
```

## Models and concurrency

Models inherit the base in `contract`. Do not use `dataclasses` or a raw `pydantic.BaseModel`. Spawn concurrent work with `asyncio.TaskGroup`. Do not call `asyncio.create_task`.

## State

Do not keep a mutable container at module level. Pass state in arguments.

## Imports

Do not import a private name (`_name`) from another package. The exception is a missing public API, marked on the import:

```python
# arch-allow-private-import: no public API for this call
from other_lib import _secret
```

## Budgets

`arch_budgets.toml` caps module length and the two waiver markers. Lowering a budget is fine. Raising one is a decision in the same change that needs it.

## Commands

From this directory:

```bash
uv run poe check
```

`poe check` formats, lints, checks imports, runs the four architecture rules, typechecks, and tests.
