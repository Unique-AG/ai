---
name: uv
description: Manage Python dependencies, lock files, and project environments using the uv package manager.
license: MIT
compatibility: claude cursor opencode
metadata:
  version: "1.0.0"
  languages: python
  audience: developers
  workflow: automation
  since: "2026-02-25"
---

## What I do

I handle the full uv dependency-management lifecycle:

- **Add or remove packages** — update `pyproject.toml` and `uv.lock` in one step
- **Sync the environment** — install exactly what the lock file specifies, nothing more
- **Regenerate the lock file** — after you edit `pyproject.toml`, safely re-resolve without unintended upgrades
- **Run commands in the project environment** — no manual `source .venv/bin/activate` needed
- **Initialise a new project** — create `pyproject.toml` and `uv.lock` from scratch, or migrate from `requirements.txt`

## When to use me

- Use this skill when the project is uv-managed (for example, `uv.lock` exists, or the team standard is uv).
- You want to add, update, or remove a dependency
- You pulled a branch and need the environment to match the updated lock file
- You edited `pyproject.toml` directly and need the lock file regenerated
- You want to run a script, test suite, or tool inside the project's virtual environment
- You are starting a new Python project with uv, or migrating from pip/requirements.txt

## Use Instead [if available]

- Use `poetry` when the project is Poetry-managed (for example, `poetry.lock` is the lockfile of record).
- Use `ci-fix` when your primary goal is diagnosing/remediating a failing CI run instead of general dependency work.

## Example usage

```
/uv add requests
/uv add --dev pytest
/uv remove httpx
/uv sync
/uv lock
/uv run pytest
/uv init
```

---

## Workflow

### Adding and removing dependencies

**Add a runtime dependency** (goes into `[project] dependencies` in `pyproject.toml`):

```bash
uv add <package>           # e.g. uv add requests
uv add "<package>>=2.0"    # with version constraint
```

**Add a dev dependency** (goes into `[dependency-groups] dev` — PEP 735, uv's preferred format):

```bash
uv add --dev <package>     # e.g. uv add --dev pytest ruff
```

Dev dependencies are installed in the development environment only and are excluded from production installs. Use `--dev` for test runners, linters, formatters, and other tooling.

**Remove a dependency**:

```bash
uv remove <package>        # removes from pyproject.toml and updates uv.lock
```

After every `add` or `remove`, uv automatically:
1. Updates `pyproject.toml`
2. Resolves all constraints and regenerates `uv.lock`
3. Installs or uninstalls the package in the active environment

**Version resolution summary**: uv prints the resolved version for each new package, e.g. `+ requests==2.32.3`. If a conflict is detected (a new package's constraints clash with existing ones), uv reports the conflict with the involved packages and constraints — fix the version bounds in `pyproject.toml` and retry.

---

### Syncing the environment

`uv sync` installs **exactly** what `uv.lock` specifies — no more, no less. It is the canonical way to bring an environment into alignment with the lock file.

```bash
uv sync
```

**When to use it:**

- After `git pull` when teammates updated `uv.lock`
- After checking out a branch with different lock file state
- After manually editing `pyproject.toml` followed by `uv lock` (run sync to apply)
- After cloning a repository for the first time

**Already in sync**: If the environment already matches the lock file, `uv sync` exits cleanly with no output. It is safe to run on every `git pull` as a habit.

**Dev vs production sync**: By default, `uv sync` includes dev dependencies. Pass `--no-dev` to sync only runtime dependencies (mirrors production).

```bash
uv sync --no-dev    # production-only install
```

---

### Regenerating the lock file

Use `uv lock` after editing `pyproject.toml` directly — for example, changing a version constraint, adding a new dependency entry by hand, or removing one.

**Safe default — no unintended upgrades:**

```bash
uv lock
```

By default, `uv lock` resolves only what has changed. Packages already in the lock file are preserved at their current versions if they still satisfy the updated constraints. This is safe to run after any `pyproject.toml` edit.

**Upgrade all dependencies to latest compatible versions:**

```bash
uv lock --upgrade
```

This re-resolves all packages to the latest versions permitted by the constraints in `pyproject.toml`. Review the lock diff carefully before committing.

**Upgrade a single package:**

```bash
uv lock --upgrade-package <package>    # e.g. uv lock --upgrade-package requests
```

Upgrades only the named package (and its transitive dependencies if required). All other resolved versions remain unchanged.

**When to use each variant:**

| Scenario | Command |
|---|---|
| Edited version constraint in `pyproject.toml` | `uv lock` |
| Removed a dependency from `pyproject.toml` | `uv lock` |
| Want to pick up security patch for one package | `uv lock --upgrade-package <pkg>` |
| Periodic refresh of all deps to latest | `uv lock --upgrade` |

After regenerating the lock file, run `uv sync` to apply the changes to your environment.

---

### Running commands in the project environment

`uv run` executes any command inside the project's virtual environment — without requiring manual activation.

```bash
uv run <command>
```

**Examples:**

```bash
uv run pytest                        # run tests
uv run pytest tests/unit/ -v        # with arguments
uv run python src/main.py           # run a script
uv run ruff check .                 # run a tool
uv run python -m mypackage          # module invocation
```

**Auto-sync behaviour**: Before running the command, uv automatically syncs the environment if `uv.lock` has changed since the last sync. This means you never need to remember to run `uv sync` before executing a command — `uv run` handles it.

`uv run pytest` is equivalent to:
```bash
source .venv/bin/activate
uv sync
pytest
```

...but in a single command, with no shell state side-effects.

**Replaces manual venv activation**: Use `uv run <cmd>` instead of `source .venv/bin/activate && <cmd>`. This works consistently across platforms and CI environments.

---

### Initialising a new project

**Start a new uv-managed project** in the current directory:

```bash
uv init
```

This creates:
- `pyproject.toml` with a minimal `[project]` section
- `uv.lock` (empty lock, ready for `uv add`)
- `.python-version` (if Python is pinned)

**Pin a specific Python version:**

```bash
uv python pin 3.12    # writes .python-version with "3.12"
```

uv reads `.python-version` automatically on every operation. Pin the version early to ensure consistency across machines and CI.

**Migrate from `requirements.txt`:**

1. Create `pyproject.toml` if it doesn't exist: `uv init`
2. Copy your dependencies into `[project] dependencies`:
   ```toml
   [project]
   dependencies = [
     "requests>=2.28",
     "click>=8.0",
   ]
   ```
3. Generate the lock file: `uv lock`
4. Sync the environment: `uv sync`
5. Delete `requirements.txt` once the migration is verified

For dev requirements (from `requirements-dev.txt`), add them with `uv add --dev <package>` instead of copying manually, so they land in `[dependency-groups] dev`.

---

## Tips for Success

1. **`uv run` replaces venv activation** — always use `uv run <cmd>` instead of activating `.venv` manually. It works in CI without any setup steps.

2. **`uv lock` is safe by default** — it will not upgrade packages that already satisfy your constraints. Run it freely after any `pyproject.toml` edit.

3. **Always review the lock diff after `--upgrade`** — `uv lock --upgrade` can pull in breaking changes. Check `git diff uv.lock` before committing and run your test suite.

4. **Use `uv add --dev` for test and lint tools** — keeping pytest, ruff, mypy, and similar tools in `[dependency-groups] dev` ensures they are never installed in production.

5. **Run `uv sync` after every `git pull`** — or just use `uv run <cmd>` and let auto-sync handle it. Either way, your environment will always match the lock file.

6. **Check uv is installed before starting**: `uv --version`. Install with `curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv` if missing.

7. **Commit `uv.lock` to version control** — the lock file is the source of truth for reproducible environments. Never add it to `.gitignore`.
