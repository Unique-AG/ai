# Feature

Paste this into the package's existing `AGENTS.md` when that file exists. Fill the blanks.

```markdown
## <feature name>

Lives in `<layer>/<module>`. Tests live beside that path under `tests/`.

Allowed imports for this feature: `<list>`.
```

If the package has no `AGENTS.md`, do not add one. Add code and tests in the modules and style that package already uses. Do not introduce `contract` or the four checks.

Do not add a `pyproject.toml`, a CI workflow, `arch_budgets.toml`, or a layers document. Add an import-linter row only when the package already has import-linter and this feature adds an allowed edge.
