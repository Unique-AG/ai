---
name: git-conventional-commits
description: Guide and commit messages to match the semantic format validated by CI
---

# When to use

- When the user authors commits 
- When the user asks about conventional commits

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

## Commit Body

- You can use markdown text here