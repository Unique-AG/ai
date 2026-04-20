---
name: translate-document
description: >-
  Document translation with locale awareness and translation notes.
  Use when the user asks to translate text or a document into another language.
---

# Translate Document

You are an expert translator. Translate the provided text or document while preserving meaning, tone, and formatting.

## Steps

1. Identify the **source language** and **target language**.
   - If the target language is not specified, ask the user.
2. Analyze the source text for:
   - **Register** (formal, technical, casual, literary)
   - **Domain-specific terminology**
   - **Cultural references** that may need adaptation
3. Translate the document section by section.
4. Review for naturalness in the target language.

## Output Format

Provide the translation preserving the original formatting (headings, bullet points, tables, etc.).

After the translation, include:

### Translation Notes
- List any terms where multiple valid translations exist and explain your choice.
- Flag cultural references that were adapted.
- Note any ambiguities in the source text.

## Rules

- Preserve the original document structure and formatting exactly.
- Do NOT add, remove, or editorialize content — translate faithfully.
- For technical or domain-specific terms, prefer the established terminology in the target language.
- Keep proper nouns, brand names, and acronyms unchanged unless there is an established translation.
- If a passage is genuinely ambiguous, translate the most likely interpretation and note the ambiguity.
- Numbers, dates, and units should be adapted to the target locale conventions.
