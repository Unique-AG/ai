---
name: git-conventional-commits
description: Guide branch creation, commit messages, and titles so the repo’s semantic workflow is enforced
license: MIT
compatibility: claude cursor opencode
metadata:
  version: "1.0.0"
  languages: all
  audience: developers
  workflow: documentation
  since: "2026-02-25"
---

# When to use

- When the user authors commits 
- When the user asks about conventional commits

## Use Instead [if available]

- Use `pr-create` for end-to-end PR title/body drafting and Jira-linking workflow.
- Use `github-pull-request-handling` for resolving and replying to existing PR review conversations.

## Allowed types

Use exactly one of these types in PR titles and commits:

| Type          | Purpose                                     |
|---------------|---------------------------------------------|
| `chore`       | Maintenance, tooling, config changes        |
| `ci`          | CI/CD pipeline changes                      |
| `deploy`      | Deployment-related changes                  |
| `docs`        | Documentation only                          |
| `feat`        | New feature                                 |
| `fix`         | Bug fix                                     |
| `improvement` | General improvement (non-feature, non-fix)  |
| `refactor`    | Code refactoring, no behavior change        |
| `test`        | Adding or updating tests                    |

## Format

```
<type>[(scope)]: <description>
```

- **Scope** (optional): Must match `[a-z:_-]+` (lowercase letters, digits, underscores, colons, hyphens). Examples: `sdk`, `api`, `my_component`.
- **Description**: Short, imperative summary. No period at the end.

## Commit Summary 

- `feat(toolkit): add streaming support`
- `feat(sdk): update message endpoint`
- `ci: add semantic PR validation`

## Branch & commit workflow

1. **Check current branch**
   - Run `git branch --show-current`; do not commit directly to `master`/`main`
   - If you are still on the base branch, ask the user for the Jira ticket ID and create a feature branch:
     - **Preferred:** `<type>/<UN-XXXXX>-<short-slug>` — e.g. `feat/un-17684-pandoc-converter`
     - **Also valid (human-authored):** `<type>/<scope>/<UN-XXXXX>-<short-slug>` — e.g. `feat/toolkit/un-17684-pandoc-converter`
   - Branches without a ticket ID are only allowed for `hotfix/*`, `release/*`, and `chore/*`
   - The ticket ID in the branch name allows tooling and `Refs:` lines to be inferred automatically

2. **Review & stage**
   - Inspect your diff (`git diff` for unstaged, `git diff --cached` for staged)
   - Stage with `git add -A` once you understand all changes
   - Optionally include `Refs: <ticket>` block in the commit body to link Jira/Ticket numbers (the repo tooling can pick this up)

3. **Write the commit**
   - Use the `<type>(<scope>): <description>` format
   - Keep the subject ≤ 72 characters without trailing period
   - Add a blank line and optional body for context, explaining why the change is necessary

4. **Examples**
   - `fix(api): handle missing authorization header`
   - `feat(payments): add refund webhook handler`
   - `chore(deps): upgrade pytest to 9.0`

## Branch/commit rules
- Always branch before committing (avoid `master`/`main`)
- Always include the Jira ticket ID in the branch name — this lets tooling auto-infer `Refs:` and keeps the ticket traceable from `git log`
- Use imperative language and don’t end with punctuation
- Keep commits focused on a single concern
- Include `Refs: <ticket>` in the commit body when the work is tracked in Jira