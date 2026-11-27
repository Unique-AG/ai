---
name: security-maintenance
description: Triage and fix Dependabot alerts, CodeQL findings and Trivy image scan alerts (search-proxy image CVEs, uv audit findings) in the ai repository. Use when the user asks to address security vulnerabilities, fix Dependabot alerts, resolve CodeQL or code scanning alerts, handle a failed Trivy image scan or uv audit run, or do security maintenance.
license: MIT
compatibility: claude cursor opencode
metadata:
  version: "2.1.0"
  languages: python
  audience: developers
  workflow: automation
  since: "2026-04-14"
---

## What I do

I drive the security maintenance workflow for the `ai` repository to keep both dashboards at zero:

- **Dependabot** — https://github.com/Unique-AG/ai/security/dependabot
- **Code scanning** — https://github.com/Unique-AG/ai/security/code-scanning. It holds CodeQL findings (code) and Trivy image scan alerts (dependency and OS package CVEs in the search-proxy image). They need different fixes, see below.

## When to use me

- "fix dependabot", "security maintenance", "fix vulnerabilities", "dependabot alerts", "CodeQL findings", "code scanning alert", "Trivy image scan failed", "uv audit"
- Periodic security maintenance sessions
- After Dependabot auto-opens `uv` PRs (we do **not** merge those directly)

---

## Release model — read first

Versions and changelogs are **fully owned by release-please** (config: `release-please-config.json`, manifest: `.release-please-manifest.json`). CI enforces this via `.github/scripts/check-no-manual-release.sh`, which **fails any PR that modifies**:

- any `CHANGELOG.md`
- `.release-please-manifest.json`
- the `version = "..."` line in any `pyproject.toml`

Because of that:

- **Never** edit `CHANGELOG.md` or bump `version` by hand. Do **not** use the `release-process` skill to justify manual edits in security PRs — that skill documents automation, not hand bumps.
- Drive the next release entries through **conventional commit subjects** (see `git-conventional-commits`). For Dependabot/CodeQL fixes use `fix(<scope>): ...` so release-please groups them under "Bug Fixes". Use `chore(deps): ...` only for risk-free dep bumps you don't want to surface in user-facing notes (it's hidden in the changelog).
- One commit per PR is fine; release-please derives bumps per workspace package from the commit subject + changed paths.

## Dependabot workflow

**Never merge Dependabot `uv` auto-PRs.** Use `constraint-dependencies` in the root `pyproject.toml` instead. The `docker` and `github-actions` group PRs are different: review and merge them normally. The docker entry in `.github/dependabot.yml` ignores python minor bumps and this repo's own image tags (release-please owns those).

1. **List alerts** — see [gh commands reference](references/gh-commands.md). Always paginate (`gh api --paginate`); the Dependabot endpoint is cursor-paged and a single `per_page=100` call silently caps at 100.
2. **Find fix version** from the alert JSON.
3. **Add/bump `constraint-dependencies`** in root `pyproject.toml` with `"<package>>=<fixed-version>"`.
4. **Handle `exclude-newer` conflicts** — if the fix version is within the 3-day rolling window, add an `exclude-newer-package` timestamp (day after latest PyPI upload). See [exclude-newer reference](references/exclude-newer.md).
5. **Prune stale `exclude-newer-package` entries** — remove any timestamp older than 3 days (redundant, global window already covers it). Keep `= false` entries.
6. **Relock** — `uv lock --refresh`, with a uv that satisfies `required-version` in the root `[tool.uv]` (it refuses to run otherwise; upgrade with `brew upgrade uv`). If resolution fails, bump the timestamp and retry.
7. **Branch and commit** — branch `fix/dependabot-<pkg>-<ver>` (single CVE) or `fix/security-<date>` (batch). Subject: `fix(deps): bump <pkg> to >=<ver> (GHSA-xxxx)` or `fix(security): batch dependabot fixes <date>`. Do **not** touch `CHANGELOG.md` or any `version = ...` field — release-please will pick the commit up on the next standing Release PR.
8. **Open PR, then close Dependabot auto-PRs** after merge (they won't auto-close because we ship via constraints, not by merging their lockfile bump).

## CodeQL workflow

1. **List findings** — see [gh commands reference](references/gh-commands.md). Paginate the same way.
2. **Read the rule and flagged code** in context.
3. **Fix the code** — see [common CodeQL patterns](references/codeql-patterns.md).
4. **Branch and PR** — same shape as Dependabot. Use `fix(<package-or-area>): <what was hardened> (CodeQL <rule-id>)`. Again: no manual changelog/version edits.

## Trivy image alerts (code scanning)

These alerts sit next to CodeQL in the code scanning dashboard but are not code issues, so do not use the CodeQL workflow. Recognise them by `tool.name == "Trivy"` and a category like `trivy-image/search_proxy` (a fresh build of `main`) or `trivy-image-release/search_proxy` (a published image). They come from the `[Security] Trivy Image Scan` workflow, which runs every Monday at 06:00 UTC and on demand, and fails on any fixable CRITICAL or HIGH finding.

1. **List and read**: see [gh commands reference](references/gh-commands.md). The alert message has the package, installed version and fixed version.
2. **Route by `location.path`**:
   - `app/.venv/lib/python3.12/site-packages/<pkg>-<version>.dist-info/METADATA` is a Python dependency, often transitive. Fix it with the Dependabot workflow steps 3 to 8: bump `constraint-dependencies` to the fixed version, relock, `fix(security): ...` PR.
   - `usr/local/lib/python*/site-packages/<pkg>...` (for example `pip`) would be a Python package from the base image, outside the virtual environment. Do not add a constraint, and `apt-get upgrade` does not update it. Bump the base image digest in the Dockerfile.
   - A `location.path` that is just the image name (for example `unique-ag/ai/search-proxy`) is a Debian package in the image, and the message names it (`zlib1g`, ...). Do not add a constraint. A rebuild picks it up through `apt-get upgrade` in the runtime stage of the Dockerfile; if that is not enough, bump the base image digest.
3. **No manual dismiss.** The alert closes when the next scan on `main` with the same category no longer reports it. After the fix merges, re-run the scan on `main` (see the gh commands reference) or wait for Monday. That closes `trivy-image/` alerts only. A `trivy-image-release/` alert stays open until a fixed image is published and the `source=release` scan runs.
4. **Released images.** The scan summary shows the days until the next scheduled release. Use the `hotfix-backport` skill only when that is more than about 3 days away, and a person decides.

## uv audit

`[Security] uv Audit` runs `uv audit` on the root `uv.lock` every Monday and on PRs that touch the lock (report only on PRs). Locally: `uv audit --preview-features audit-command --frozen`. It finds lock vulnerabilities that Dependabot may not have raised yet. Fix them with the Dependabot workflow.

## Batch session

1. List all Dependabot alerts, CodeQL findings and Trivy image alerts (paginated), and run `uv audit`.
2. Prune stale `exclude-newer-package` entries.
3. Fix Dependabot alerts, Trivy alerts on Python packages and `uv audit` findings (mechanical: constraints + relock).
4. Fix CodeQL findings (code changes).
5. Single branch for related fixes, separate branches for unrelated areas.
6. Commit with `fix(...)` subjects so release-please attributes bumps to the right workspace package(s) on the next Release PR.
7. Create PR(s), let CI run `check-no-manual-release.sh`, then close any resolved Dependabot `uv` auto-PRs after merge. Re-run the Trivy image scan on `main` to close `trivy-image/` alerts; `trivy-image-release/` alerts need a release scan after the fix ships.

## Tips

- **Never merge Dependabot `uv` auto-PRs** — `constraint-dependencies` persists across relocks; auto-PRs only edit `uv.lock`.
- **Never touch `CHANGELOG.md`, `.release-please-manifest.json`, or `version = ...`** — `check-no-manual-release.sh` will block the PR.
- **Use `fix(...)` not `chore(deps): ...`** when you want the fix to appear in user-facing release notes; `chore` is hidden by the changelog config.
- **Round timestamps up** — day *after* latest artifact upload (`uv` uses strict `<` on individual wheel upload times).
- **Batch when possible** — one PR reduces noise; release-please still attributes per workspace package.
- **Prune stale timestamps** — entries older than the 3-day window are redundant.
- **Check both dashboards** — Dependabot and code scanning are independent, and code scanning holds both CodeQL and Trivy alerts.
