# Example Skill Files

These `.md` files are example skills for the SkillTool. To use them:

1. Create a **scope** in the knowledge base (or use an existing one).
2. Upload these `.md` files into that scope.
3. Set `skill_tool_config.scope_id` to the scope's ID in the space configuration.
4. Set `skill_tool_config.enabled` to `true`.

The SkillTool will automatically discover all `.md` files in the configured scope
and make them available to the agent.

## File format

Each skill file uses **YAML frontmatter** to declare its metadata:

```markdown
---
skill_name: summarize-document
description: Structured document summarization with executive summary
when_to_use: When the user asks to summarize or get an overview of a document
---

# Summarize Document

You are an expert document summarizer...
```

| Frontmatter key | Required | Purpose                                                     |
|-----------------|----------|-------------------------------------------------------------|
| `skill_name`    | No       | Skill identifier (defaults to file name without `.md`)      |
| `description`   | Yes      | Short description shown to the LLM in the skill listing     |
| `when_to_use`   | Yes      | Guidance for the LLM on when to activate this skill         |

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
