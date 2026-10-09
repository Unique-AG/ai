# Practices

Read the one skill that matches the work you are about to do. Do not read the rest. Ask the user before you apply a practice that the copied `AGENTS.md` does not already require. If they say no, follow the copied rules.

These files stay in their repos. Do not copy a skill into the package.

In the ai repo, skills are `.claude/skills/<name>/SKILL.md`. In the monorepo, skills are `.cursor/skills/<name>/SKILL.md`. If the package is in a repo that does not contain the skill, ask before borrowing it.

## Python

| Work | Skill | Repo |
| --- | --- | --- |
| Add or lock a dependency | `uv` | ai |
| Write tests | `python-testing` | ai |
| A failure path | `add-error-handling` | ai |
| A public docstring | `python-code-documentation-guidelines` | ai |
| After editing Python | `python-ruff-after-edit` | monorepo |

`python-testing` wants `test_<unit>__<behavior>__<condition>`, a three-part docstring on every test, and `@pytest.mark.ai`. The skeleton test is `test_model_rejects_extra_fields` and has neither. Ask before you switch the package to that style.

`add-error-handling` is useful for specific exceptions, `raise ... from`, and not logging secrets. Ask before you add retries, correlation ids, or a new log format. This basis has no shared log format outside MCP.

A package that uses `poetry.lock` uses the `poetry` skill instead of `uv`.

## Any project

| Work | Skill | Repo |
| --- | --- | --- |
| The task is still vague | `clarify-task` | both |
| A commit | `git-conventional-commits` | ai |
| A commit | `git-branch-commit` | monorepo |
| Before a pull request | `pr-self-review`, then `pr-create` | ai |
| A large diff | `pr-split` | ai |
| Generated code reads like filler | `deslop` | monorepo |

## Already required by the host

When the package is in the monorepo, `AGENTS.md` there already says to read `SECURITY-RULES.md` before writing code. Follow it. Do not ask to skip it, and do not copy it into this package.

`conduct-standards` applies only under `conduct/`. `security-maintenance-python-bundles` applies only to assistant images.
