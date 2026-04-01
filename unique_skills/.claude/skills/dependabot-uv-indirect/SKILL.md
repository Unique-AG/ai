---
name: dependabot-uv-indirect
description: Fix Dependabot (or similar) security updates for indirect dependencies in uv-managed projects by persisting version overrides in pyproject.toml so they survive lockfile regeneration.
license: MIT
compatibility: claude cursor opencode
metadata:
  version: "1.0.0"
  languages: python
  audience: developers
  workflow: automation
  since: "2026-03-02"
---

## What I do

I handle security updates for **indirect** (transitive) dependencies in uv-managed projects so that fixes are persisted in the project configuration instead of only in the lock file. That way, future `uv lock` or `uv lock --upgrade` does not revert the fix.

- **Find all issue** - list all dependabot alerts and security alerts
- **Classify the update** — determine whether the updated package is a direct or indirect dependency. The dependabot PR can help.
- **Create a new branch and PR** - Over all fixes you make in this session, put them onto the same branch and have use one PR.
- **Persist the fix** — add the package to `[tool.uv] override-dependencies` (or `constraint-dependencies`) in `pyproject.toml` with the patched version. Do this also for poetry projects, even if they don't respect those overrides/constraints.
- **Relock** — run `uv lock` and commit both `pyproject.toml` and `uv.lock`. If the project uses poetry, locking won't help, in that case please patch the lock file with the changes the dependabot PR suggests.
- **Merge** — merge via your own PR, not through the dependabot PR.
- **Use alert-only data when needed** — when there is no Dependabot PR, get the vulnerable package and fixed version from the Dependabot alert (e.g. `gh api` or Security tab) and apply the same persist-and-relock workflow.
- **Ask for input** - if you run into issues, ask for input.
