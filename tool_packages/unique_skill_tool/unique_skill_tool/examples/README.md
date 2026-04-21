# Example Skill Files

These `.md` files are example skills for the SkillTool. To use them:

1. Create one or more **scopes** in the knowledge base (or use existing ones).
2. Upload these `.md` files directly into those scopes. Sub-folders are
   not traversed automatically — add each sub-folder's scope ID to
   `scope_ids` if you want its skills loaded.
3. Add every scope ID to `skill_tool_config.scope_ids` in the space
   configuration (the field accepts a list — click "Add Item" for each).
4. Set `skill_tool_config.enabled` to `true`.

The SkillTool fetches all `.md` files from the configured scopes. Only the
scopes listed in `scope_ids` are queried — sub-folders are not traversed
automatically, so add each scope you want searched explicitly. Per-user
folder permissions are enforced by the backend ACL, so users only see
skills in folders they can access.

## File format

Each skill file uses **YAML frontmatter** to declare its metadata:

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

| Frontmatter key | Required | Purpose                                                     |
|-----------------|----------|-------------------------------------------------------------|
| `name`          | No       | Skill identifier (defaults to file name without `.md`)      |
| `description`   | Yes      | Short description shown to the LLM in the skill listing — include guidance on when to activate this skill |

Everything below the frontmatter is the **skill body** — the full prompt
instructions injected when the agent invokes the skill.

## Included examples

| File                      | Purpose                                    |
|---------------------------|--------------------------------------------|
| `summarize-document.md`   | Structured document summarization          |
| `analyze-data.md`         | Tabular / numerical data analysis          |
| `draft-email.md`          | Professional email drafting                |
| `review-contract.md`      | Contract risk analysis and review          |
| `translate-document.md`   | Document translation with locale awareness |
