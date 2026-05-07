---
name: ci-local-parity
description: Reproduce ai-repo PR checks locally with Poe and CI scripts, including per-package typecheck and coverage behavior. Use when validating changes before push or when user asks which local commands match CI.
license: MIT
compatibility: claude cursor opencode
metadata:
  version: "1.0.0"
  languages: python
  audience: developers
  workflow: automation
  since: "2026-05-07"
---

## What I do

I run the `ai` repository checks locally with the closest possible parity to PR CI:

- Map changed files to affected packages
- Run package checks in CI order (`format --check`, lint, test, types, coverage, depcheck)
- Apply package-specific behavior from `.github/actions/get-packages-matrix/package_configuration.json`
- Use baseline/diff mode for packages that use it, strict mode for packages that require zero errors
- Call out CI checks that are not fully reproducible through Poe alone

## When to use me

- User asks how to run CI checks locally in `ai`
- User wants the exact local commands before opening/updating a PR
- User asks about Poe tasks vs CI scripts and where they differ
- You need to validate one package or all changed packages with CI-like behavior

## Use Instead [if available]

- Use `ci-fix` when the primary task is diagnosing an already-failed CI run.
- Use `ruff` for lint/format-only cleanup without CI parity requirements.
- Use `uv` for dependency/lockfile maintenance not tied to CI parity.

## Example usage

```
/ci-local-parity
/ci-local-parity unique_toolkit
/ci-local-parity changed-packages
```

---

## Workflow

### Step 0: Preconditions

Run from repository root:

```bash
cd /Users/aurelgruber/Unique/code/ai
```

Ensure tooling is available:

```bash
uv --version
uv run poe --help
```

If `uv` is missing, stop and ask the user to install/repair it before proceeding.

---

### Step 1: Determine target packages

For changed packages in current branch:

```bash
BASE_REF=origin/main
git fetch origin main
git diff --name-only "$BASE_REF"...HEAD
```

Map changed files to package directories using:

- `.github/actions/get-packages-matrix/package_configuration.json`

Treat the `dir` field as canonical package path.

If the user asked for one package, skip auto-detection and use that package directly.

---

### Step 2: Run baseline package checks (CI-like order)

Inside each package directory (`cd <package_dir>`), run:

```bash
uv run ruff format --check .
uv run poe lint
uv run poe test
uv run poe depcheck
```

Then run typecheck + coverage per Step 3 and Step 4 (mode differs by package).

Notes:

- CI lint uses both format check and lint check.
- `poe format` is not equivalent to CI lint because it writes files.

---

### Step 3: Typecheck mode (strict vs baseline)

Read package behavior from matrix flags:

- `typecheck_use_baseline`
- `typecheck_require_zero_errors`

#### Strict/full mode

Use for packages with `typecheck_use_baseline: false` and for any package requiring zero errors:

- `toolkit`
- `sdk`
- `skill_tool`

Command:

```bash
uv run poe typecheck
```

#### Baseline mode (new errors vs base)

Use for packages with `typecheck_use_baseline: true`:

```bash
uv run poe ci-typecheck
```

This routes to `.github/scripts/dev.sh typecheck` and mirrors CI’s baseline behavior closely.

Fallback if `ci-typecheck` task does not exist in a package:

```bash
bash "$(git rev-parse --show-toplevel)/.github/scripts/dev.sh" typecheck --dir .
```

---

### Step 4: Coverage mode (diff-based parity)

Preferred CI-like command:

```bash
uv run poe ci-coverage
```

Fallback if task missing:

```bash
bash "$(git rev-parse --show-toplevel)/.github/scripts/dev.sh" coverage --dir .
```

Full-package (non-diff) coverage when requested:

```bash
uv run poe coverage
```

---

### Step 5: Apply package-specific CI arguments

From matrix config:

- `sdk` test args: `-m "not integration"`
- `toolkit` install extras: `--extra fastapi --extra monitoring` (CI setup behavior)

For SDK parity:

```bash
uv run poe test -- -m "not integration"
```

For toolkit parity, if needed before tests/coverage:

```bash
uv sync --locked --inexact --extra fastapi --extra monitoring
```

---

### Step 6: CI checks that are not pure Poe parity

Call these out explicitly in summary; do not claim full parity:

- Dependency job (`ci-dependency-checks.yaml`) uses min-deps installation strategy via `.github/actions/run-min-tests-and-deptry` (not the same as `poe depcheck`).
- Config compatibility job (`ci-config-check.yaml`) uses `unique_toolkit._common.config_checker` export/check flow.
- PR policy checks:
  - PR title validation
  - no-manual-release script
  - gatekeeper status aggregation

Run these manually only when needed with their underlying scripts/workflows.

---

## Package quick recipes

### One package, closest PR-CI parity

```bash
cd <package_dir>
uv run ruff format --check .
uv run poe lint
uv run poe test
uv run poe depcheck
uv run poe ci-typecheck || bash "$(git rev-parse --show-toplevel)/.github/scripts/dev.sh" typecheck --dir .
uv run poe ci-coverage || bash "$(git rev-parse --show-toplevel)/.github/scripts/dev.sh" coverage --dir .
```

### Strict packages (`toolkit`, `sdk`, `skill_tool`)

```bash
cd <package_dir>
uv run ruff format --check .
uv run poe lint
uv run poe test
uv run poe depcheck
uv run poe typecheck
uv run poe ci-coverage || bash "$(git rev-parse --show-toplevel)/.github/scripts/dev.sh" coverage --dir .
```

For `sdk` test parity:

```bash
uv run poe test -- -m "not integration"
```

---

## Tips for success

1. **Always include `ruff format --check`** for CI lint parity.
2. **Use matrix flags, not assumptions** for strict vs baseline typecheck mode.
3. **Prefer `ci-*` Poe tasks** for diff/baseline parity, then fall back to `dev.sh`.
4. **Do not over-claim parity**: deps/config/policy jobs are only partially reproducible via Poe.
5. **Run from repo root first** so relative script paths and git base refs work reliably.
