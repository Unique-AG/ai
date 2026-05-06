# Example Skills

These folders are example skills for the SkillTool. They follow the
official Agent Skills protocol — see
[Agent Skills](https://agentskills.io/home)
— where **each skill is a folder** containing a `SKILL.md` entrypoint:

```
<skill-name>/
  SKILL.md          (required: name + description + body)
  scripts/          (optional: executable code)
  references/       (optional: documentation)
  assets/           (optional: templates, resources)
  ...               (optional: appearance and dependencies)
```

Only files whose basename is `SKILL.md` are registered as skills. Other
markdown files in the same folder (`README.md`, `references/*.md`, etc.)
are treated as assets, not separate skills.

Per-user folder permissions are enforced by the backend ACL, so users
only see skills in folders they can access.

## File format

Each `SKILL.md` uses **YAML frontmatter** to declare its metadata:

```markdown
---
name: summarize-document
description: >-
  Structured document summarization with executive summary.
  Use when the user asks to summarize or get an overview of a document.
---

# Summarize Document

You are an expert document summarizer...
```

| Frontmatter key | Required | Purpose                                                                                                  |
| --------------- | -------- | -------------------------------------------------------------------------------------------------------- |
| `name`          | Yes      | Skill identifier (kebab-case, 1–64 chars). Used as the tool argument value.                              |
| `description`   | Yes      | Short description shown to the LLM in the skill listing — include guidance on **when** to activate this skill. |

Everything below the frontmatter is the **skill body** — the full prompt
instructions injected when the agent invokes the skill.

## Included examples

| Folder              | Purpose                                    |
| ------------------- | ------------------------------------------ |
| `analyze-data/`     | Tabular / numerical data analysis          |
| `analyze-factsheet/`| Factsheet data analysis                    |
| `draft-email/`      | Professional email drafting                |
| `review-contract/`  | Contract risk analysis and review          |
