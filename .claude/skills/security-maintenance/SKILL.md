---
name: security-maintenance
description: Triage and fix Dependabot alerts and CodeQL findings in the ai repository. Use when the user asks to address security vulnerabilities, fix Dependabot alerts, resolve CodeQL issues, or do security maintenance.
license: MIT
compatibility: claude cursor opencode
metadata:
  version: "1.1.0"
  languages: python
  audience: developers
  workflow: automation
  since: "2026-04-14"
---

## What I do

I drive the security maintenance workflow for the `ai` repository to keep both dashboards at zero:

- **Dependabot** — https://github.com/Unique-AG/ai/security/dependabot
- **CodeQL** — https://github.com/Unique-AG/ai/security/code-scanning

## When to use me

- "fix dependabot", "security maintenance", "fix vulnerabilities", "dependabot alerts", "CodeQL findings"
- Periodic security maintenance sessions
- After Dependabot auto-opens PRs (we do **not** merge those directly)

---

## Dependabot workflow

**Never merge Dependabot auto-PRs.** Use `constraint-dependencies` in the root `pyproject.toml` instead.

1. **List alerts** — see [gh commands reference](references/gh-commands.md)
2. **Find fix version** from the alert JSON
3. **Add/bump `constraint-dependencies`** in root `pyproject.toml` with `"<package>>=<fixed-version>"`
4. **Handle `exclude-newer` conflicts** — if the fix version is within the 2-week rolling window, add an `exclude-newer-package` timestamp (day after latest PyPI upload). See [exclude-newer reference](references/exclude-newer.md)
5. **Prune stale `exclude-newer-package` entries** — remove any timestamp older than 2 weeks (redundant, global window already covers it). Keep `= false` entries.
6. **Relock** — `uv lock --refresh`. If resolution fails, bump the timestamp and retry.
7. **Version bump affected packages** — changelog entry + patch bump only for workspace packages whose own `pyproject.toml` was modified (CI enforces this per-package, not workspace-wide). Use the `changelog-pyproject` skill.
8. **Branch and PR** — branch `fix/dependabot-<pkg>-<ver>` or `fix/security-<date>` for batches. Close Dependabot auto-PRs after merge.

## CodeQL workflow

1. **List findings** — see [gh commands reference](references/gh-commands.md)
2. **Read the rule and flagged code** in context
3. **Fix the code** — see [common CodeQL patterns](references/codeql-patterns.md)
4. **Version bump, branch, PR** — same as Dependabot

## Batch session

1. List all Dependabot alerts and CodeQL findings
2. Prune stale `exclude-newer-package` entries
3. Fix Dependabot alerts (mechanical)
4. Fix CodeQL findings (code changes)
5. Single branch for related fixes, separate for unrelated
6. Bump only packages whose `pyproject.toml` was modified
7. Create PR(s), close resolved Dependabot auto-PRs after merge

## Tips

- **Never merge Dependabot auto-PRs** — `constraint-dependencies` persists across relocks
- **Round timestamps up** — day *after* latest artifact upload (`uv` uses strict `<` on individual wheel upload times)
- **Batch when possible** — one PR reduces version bump noise
- **Prune stale timestamps** — entries older than the 2-week window are redundant
- **Check both dashboards** — Dependabot and CodeQL are independent
