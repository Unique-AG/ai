---
name: security-maintenance
description: Triage and fix security vulnerabilities in the ai repository and monorepo Python services. Use when the user asks to address security vulnerabilities, fix Dependabot alerts, resolve CodeQL/Trivy findings, or do security maintenance.
license: MIT
compatibility: claude cursor opencode
metadata:
  version: "1.2.0"
  languages: python
  audience: developers
  workflow: automation
  since: "2026-04-14"
---

## What I do

I drive the security maintenance workflow for two repositories:

### ai repository
- **Dependabot** — https://github.com/Unique-AG/ai/security/dependabot
- **CodeQL** — https://github.com/Unique-AG/ai/security/code-scanning

### monorepo (assistants bundles)
- **Trivy** — https://github.com/Unique-AG/monorepo/security/code-scanning (daily container image scans)
- **Renovate** — automated dependency and base image PRs (weekly, scoped to `python/assistants/bundles/**`)

## When to use me

- "fix dependabot", "security maintenance", "fix vulnerabilities", "dependabot alerts", "CodeQL findings", "Trivy findings"
- Periodic security maintenance sessions
- After Dependabot auto-opens PRs (we do **not** merge those directly)
- After Trivy flags CVEs in the monorepo security tab

---

## Dependabot workflow

**Never merge Dependabot auto-PRs.** Use `constraint-dependencies` in the root `pyproject.toml` instead.

1. **List alerts** — see [gh commands reference](references/gh-commands.md)
2. **Find fix version** from the alert JSON
3. **Add/bump `constraint-dependencies`** in root `pyproject.toml` with `"<package>>=<fixed-version>"`
4. **Handle `exclude-newer` conflicts** — if the fix version is within the 2-week rolling window, add an `exclude-newer-package` timestamp (day after latest PyPI upload). See [exclude-newer reference](references/exclude-newer.md)
5. **Prune stale `exclude-newer-package` entries** — remove any timestamp older than 2 weeks (redundant, global window already covers it). Keep `= false` entries.
6. **Relock** — `uv lock --refresh`. If resolution fails, bump the timestamp and retry.
7. **Version bump all packages** — changelog entry + patch bump for each workspace package (CI enforces this). Use the `changelog-pyproject` skill.
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
6. Bump all packages once at the end
7. Create PR(s), close resolved Dependabot auto-PRs after merge

---

## Monorepo: Assistants Bundles

The monorepo Python services (`python/assistants/bundles/`) use a different security model. See [monorepo workflow reference](references/monorepo-workflow.md) for full details.

### Key differences from ai repo

| | ai repo | monorepo |
|---|---|---|
| Dependency alerts | Dependabot (auto-PRs) | Renovate (weekly, scoped) |
| Container scanning | N/A | Trivy (daily, `ignore-unfixed: true`) |
| Dependency pinning | uv workspace, root `constraint-dependencies` | Standalone uv projects, per-project `constraint-dependencies` |
| Version bumps | All workspace packages | Not required (no changelog enforcement) |

### Workflow summary

1. **List Trivy alerts** — `gh api repos/Unique-AG/monorepo/code-scanning/alerts` filtered by path
2. **Classify each CVE** — OS-level (base image) vs Python dependency vs false positive
3. **Python dependency CVEs** — add `constraint-dependencies` to the service's own `pyproject.toml` (not just the lockfile), relax exact pins if needed, `uv lock --refresh`
4. **OS-level CVEs with fix available** — update base image digest in Dockerfile; if image predates the fix, explicitly `apt-get install` the fixed package
5. **OS-level CVEs without fix** — assess real-world risk (see reference); most are false positives in containers
6. **Build locally** — `docker build` to verify, optionally run Trivy locally for validation

**Same principle as ai repo**: for security fixes, always persist the version floor in `constraint-dependencies` — never just patch the lockfile or merge an auto-PR directly.

### Quick reference: monorepo pyproject.toml

```toml
# python/assistants/bundles/core/src/pyproject.toml
[tool.uv]
constraint-dependencies = [
    "langchain-core>=1.2.22",  # CVE-2026-34070
    "pillow>=12.2.0",          # CVE-2026-40192
]
```

No `exclude-newer` window in the monorepo — constraints take effect immediately.

---

## Tips

- **Never merge Dependabot auto-PRs** (ai repo) — `constraint-dependencies` persists across relocks
- **Round timestamps up** (ai repo) — day *after* latest artifact upload (`uv` uses strict `<` on individual wheel upload times)
- **Batch when possible** — one PR reduces version bump noise
- **Prune stale timestamps** (ai repo) — entries older than the 2-week window are redundant
- **Check all dashboards** — Dependabot, CodeQL, and Trivy are independent
- **Trivy `ignore-unfixed: true`** (monorepo CI) — CI only flags CVEs with available fixes; run Trivy locally without this flag to see the full picture
- **Container false positives** — many OS-level CVEs (systemd, ncurses CLI tools, MiniZip in zlib) are unreachable in containers; assess before migrating base images
