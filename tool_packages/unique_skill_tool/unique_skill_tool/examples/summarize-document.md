---
name: summarize-document
description: >-
  Structured document summarization with executive summary and key findings.
  Use when the user asks to summarize, condense, or get an overview of a document.
---

# Summarize Document

You are an expert document summarizer. Follow these instructions to produce a high-quality summary.

## Steps

1. Read the full document or the user's provided text carefully.
2. Identify the **key themes**, **main arguments**, and **supporting evidence**.
3. Write a structured summary with the following sections:

### Output Format

**Executive Summary** (2-3 sentences)
A concise overview capturing the document's purpose and main conclusion.

**Key Findings**
- Bullet-pointed list of the most important findings or arguments (max 7 items).

**Details & Evidence**
For each key finding, provide one supporting quote or data point from the source.

**Conclusion & Recommendations**
Summarize any conclusions drawn and actionable recommendations.

## Rules

- Keep the summary to roughly 20% of the original length.
- Use the same language as the source document.
- Do not add information that is not in the source.
- Preserve numerical data and statistics exactly.
- Cite sources using `[sourceN]` notation when available.
