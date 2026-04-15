---
name: security-maintenance
description: Triage and fix Dependabot alerts and CodeQL findings in the ai repository. Use when the user asks to address security vulnerabilities, fix Dependabot alerts, resolve CodeQL issues, or do security maintenance.
license: MIT
compatibility: claude cursor opencode
metadata:
  version: "1.0.0"
  languages: python
  audience: developers
  workflow: automation
  since: "2026-04-14"
---

## What I do

I drive the security maintenance workflow for the `ai` repository to keep both dashboards at zero:

- **Dependabot** — https://github.com/Unique-AG/ai/security/dependabot
- **CodeQL** — https://github.com/Unique-AG/ai/security/code-scanning

For Dependabot alerts I persist fixes through `constraint-dependencies` and `exclude-newer-package` in the root `pyproject.toml`, then relock. For CodeQL findings I fix the flagged code directly. Both result in a PR.

## When to use me

- User says "fix dependabot", "security maintenance", "fix vulnerabilities", "dependabot alerts", "CodeQL findings", etc.
- Periodic security maintenance sessions
- After Dependabot auto-opens PRs (we do **not** merge those directly)

## Use Instead [if available]

- Use `ci-fix` for general CI failures unrelated to security
- Use `uv` for dependency management tasks that are not security-related

---

## Part 1: Dependabot Alerts

### Key principle

Dependabot auto-opens PRs that patch `pyproject.toml` / `uv.lock` directly. **Do not merge those PRs.** Instead, use the root workspace's `constraint-dependencies` section to enforce security floors, then relock. This ensures every package in the workspace picks up the fix and the constraint survives future relocks.

### Step 1: List open alerts

```bash
gh api repos/Unique-AG/ai/dependabot/alerts --jq '.[] | select(.state=="open") | "\(.number) \(.security_advisory.severity) \(.dependency.package.ecosystem):\(.dependency.package.name) — \(.security_advisory.summary)"'
```

If there are no open alerts, move on to Part 2 (CodeQL).

### Step 2: For each alert, find the fix version

The alert JSON contains the fixed version:

```bash
gh api repos/Unique-AG/ai/dependabot/alerts/<NUMBER> --jq '.security_vulnerability.first_patched_version.identifier'
```

Record the package name and minimum fixed version.

### Step 3: Add or update constraint-dependencies

Open the root `pyproject.toml`. In `[tool.uv] constraint-dependencies`, add or bump the entry:

```toml
[tool.uv]
constraint-dependencies = [
    # ... existing entries ...
    "<package>>=<fixed-version>",
]
```

If the package is already listed, bump the version floor to the fixed version.

### Step 4: Handle exclude-newer conflicts

The workspace uses `exclude-newer = "2 weeks"` which may hide the fixed version if it was published recently. To check:

1. Look up the package's release date on PyPI:
   ```bash
   uv pip index versions <package> 2>&1 | head -5
   ```
   Or check PyPI directly: `https://pypi.org/project/<package>/<version>/`

2. If the fixed version was published within the last 2 weeks (or if `uv lock` fails to resolve it), add an `exclude-newer-package` override in the root `pyproject.toml`:
   ```toml
   [tool.uv.exclude-newer-package]
   "<package>" = "YYYY-MM-DD"
   ```
   The date must be the **day after** the latest artifact upload time for that version. Round up, not down. For example, if the latest wheel was uploaded on `2026-04-08T23:45:00Z`, use `"2026-04-09"`.

3. To find the exact upload time, check the PyPI JSON API:
   ```bash
   curl -s https://pypi.org/pypi/<package>/<version>/json | python3 -c "import sys,json; d=json.load(sys.stdin)['urls']; print(max(u['upload_time_iso_8601'] for u in d))"
   ```
   Then round up to the next day.

### Step 4b: Clean up stale exclude-newer-package entries

Any `exclude-newer-package` timestamp that is older than the configured `exclude-newer` window (currently 2 weeks) is redundant — the global window already allows that version through. Remove these stale entries to keep the section minimal.

```bash
TODAY=$(date +%s)
WINDOW_DAYS=14
```

For each entry in `[tool.uv.exclude-newer-package]`, check whether the timestamp is more than 14 days in the past. If it is, delete the line. Keep entries that are:
- Set to `false` (permanent overrides, e.g. `unique-toolkit`)
- Still within the 2-week window (the version would be hidden without the override)

### Step 5: Relock

```bash
uv lock --refresh
```

If resolution fails, the `exclude-newer-package` timestamp is likely too tight. Bump it to the next day and retry.

### Step 6: Version bump all packages

Every workspace package needs a changelog entry and patch version bump. The CI enforces this via the `Changelog and Version Bump` workflow. For each package:

1. Add a changelog entry in `<package>/CHANGELOG.md` (newest-first, today's date)
2. Bump the `version` field in `<package>/pyproject.toml`
3. Relock again after bumping: `uv lock --refresh`

Use the `changelog-pyproject` skill for format guidance.

### Step 7: Create a branch and PR

- Branch naming: `fix/dependabot-<package>-<version>` or `fix/security-<date>` for batch fixes
- Do **not** merge the Dependabot auto-PRs. Close them after your fix PR is merged.
- Use the `pr-create` skill for PR creation

---

## Part 2: CodeQL Findings

### Step 1: List open findings

Visit https://github.com/Unique-AG/ai/security/code-scanning or use:

```bash
gh api repos/Unique-AG/ai/code-scanning/alerts --jq '.[] | select(.state=="open") | "\(.number) \(.rule.severity) \(.rule.id) — \(.most_recent_instance.location.path):\(.most_recent_instance.location.start_line)"'
```

### Step 2: Understand the finding

For each alert, read the rule description and the flagged code:

```bash
gh api repos/Unique-AG/ai/code-scanning/alerts/<NUMBER> --jq '{rule: .rule.id, severity: .rule.severity, description: .rule.description, path: .most_recent_instance.location.path, start_line: .most_recent_instance.location.start_line, end_line: .most_recent_instance.location.end_line}'
```

Read the flagged file and understand the vulnerability in context.

### Step 3: Fix the code

CodeQL fixes are code changes — there is no shortcut. Common patterns:

- **SQL injection**: Use parameterized queries instead of string interpolation
- **Path traversal**: Validate and sanitize file paths
- **Hardcoded credentials**: Move to environment variables or secret managers
- **Unsafe deserialization**: Use safe loaders or validate input
- **Command injection**: Use subprocess with argument lists, not shell strings

### Step 4: Version bump, branch, and PR

Same as Dependabot: changelog entry, version bump, relock, create PR.

---

## Batch workflow

When doing a full security maintenance session:

1. List all Dependabot alerts and CodeQL findings
2. Remove stale `exclude-newer-package` entries (older than 2 weeks)
3. Fix all Dependabot alerts first (they're usually mechanical)
4. Fix CodeQL findings (these require code changes)
5. Put everything on a single branch if the fixes are related, or separate branches for unrelated fixes
6. Bump all affected packages once at the end
7. Create PR(s)
8. After merge, close any Dependabot auto-PRs that are now resolved

---

## Quick reference: root pyproject.toml sections

```toml
[tool.uv]
exclude-newer = "2 weeks"                    # global rolling window
constraint-dependencies = [                   # security version floors
    "cryptography>=46.0.7",
]

[tool.uv.exclude-newer-package]
"cryptography" = "2026-04-09"                # override for packages hidden by exclude-newer
```

- `constraint-dependencies` — enforces minimum versions across the entire workspace
- `exclude-newer-package` — per-package override of the 2-week rolling window; set to the day after the latest PyPI artifact upload for the required version

## Tips

- **Never merge Dependabot auto-PRs** — always use `constraint-dependencies` so the fix persists across relocks
- **Round timestamps up** — `exclude-newer-package` dates should be the day *after* the latest artifact upload, because `uv` uses a strict `<` comparison on individual wheel upload times
- **Batch when possible** — fixing multiple alerts in one PR reduces version bump noise
- **Prune stale timestamps** — `exclude-newer-package` entries older than the 2-week window are redundant; remove them during every maintenance session to keep the config clean
- **Check both dashboards** — Dependabot and CodeQL are independent; zero on one doesn't mean zero on the other
