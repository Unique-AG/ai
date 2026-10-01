---
name: changelog-fragment
description: Decide whether an ai PR needs a changelog fragment or the `no-changelog` label, and create the fragment under .changelog/unreleased/ when it does. Use before opening a PR, when CI's "Changelog Fragment" check fails, or when asked to add a changelog entry.
license: MIT
compatibility: claude cursor opencode
metadata:
  version: "1.0.0"
  languages: all
  audience: developers
  workflow: release
---

# Changelog fragment

Each fragment is one line in the release notes of the next ai version. The release manager reads these lines to pick what goes into the monorepo release notes, so fewer and shorter is better.

## 1. Decide first (default: no fragment)

Add a fragment only for something a platform user, admin or operator notices after upgrading. Otherwise add the `no-changelog` label.

| Fragment | `no-changelog` |
|---|---|
| New capability users or admins see | Diff only adds new `LanguageModelName` members, their infos, tests, and the new names to existing model lists; the models page covers it |
| Behavior change, including defaults (e.g. how existing models behave) | Refactors, renames, typing, lint |
| New or changed config key, flag, env var, Helm value | Tests, CI, docs, tutorials, skills |
| Removal or deprecation | Dependency bumps with no behavior change |
| User-visible bug fix | Fixes to something not released yet |
| Security patch | Internals not reachable from the platform |

Tie-breaker: would the release manager put this line in the platform release notes? If not, `no-changelog`.

After adding or removing the label, re-run the CI workflow ("Re-run all jobs"). The check reads labels from the PR event, so a label change alone does not update it.

## 2. Reuse before adding

Read `.changelog/unreleased/*.yaml`. If one already describes the same change (same flag, config key or behavior, not just the same component), edit that file instead of adding another.

## 3. Create

Run from the repo root:

```bash
uv run .claude/skills/changelog-fragment/scripts/changelog_new.py \
  --kind Fixed --component "Web Search" --audience user \
  --package unique-toolkit --ticket UN-12345 \
  --body "Search results keep their source links after a retry."
```

- `--kind`, `--component`, `--audience`: values from `.changie.yaml`; the script rejects anything else.
- `--package`: release-please component names from `release-please-config.json` (e.g. `unique-toolkit`, `unique-sdk`), comma-separated.
- `--ticket`: optional, `UN-<number>`, comma-separated. Never put ticket IDs in the body.

## 4. Body rules

- One sentence, present tense, the observable effect, about 25 words at most.
- Name the exact flag, config key or env var and its default when the change is gated.
- Start a second paragraph with `Behavior change:` only when existing users get different behavior without opting in.
- No implementation details, and don't repeat the kind, component or package (they render around the body).
- Security: say what was patched, never versions or CVE/GHSA IDs.

## 5. Verify

```bash
bash .github/scripts/changelog-check.sh
```

## Examples

```yaml
component: Web Search
kind: Fixed
body: Search results keep their source links after a retry.
custom:
  Audience: user
  Package: unique-toolkit
```

```yaml
component: Chat Experience
kind: Added
body: Streaming responses can show tool progress; off by default, enable with `ENABLE_TOOL_PROGRESS=true`.
custom:
  Audience: admin
  Package: unique-orchestrator, unique-toolkit
  Ticket: UN-12345
```

```yaml
component: API / SDK
kind: Removed
body: The deprecated `Search.create(searchType="VECTOR_LEGACY")` option is removed; use `VECTOR`.
custom:
  Audience: operator
  Package: unique-sdk
```

`no-changelog` cases:

- A PR that adds `GPT_6` to `LanguageModelName` with its `LanguageModelInfo` and a test.
- A PR that moves helpers into a new module without changing behavior.
