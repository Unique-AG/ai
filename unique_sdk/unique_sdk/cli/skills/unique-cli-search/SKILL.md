---
name: unique-cli-search
description: >-
  Search the Unique AI Platform knowledge base using the unique-cli search
  command, with automatic per-turn citation tracking so cited facts render
  as clickable reference chips and `<sup>N</sup>` footnotes on the Unique
  platform. Use whenever the user asks to find, search, or query documents
  or content on Unique, including filtering by folder or metadata.
  NOTE: This search uses combined vector + full-text indexing. Excel
  (.xlsx/.xls), CSV (.csv), and image files are NOT full-text indexed,
  so they will not appear in search results. To locate these file types,
  use the unique-cli-file-management skill instead (browse folders with
  `unique-cli ls` to find them by name).
---

# Unique CLI -- Knowledge Base Search

Search the Unique knowledge base using combined vector + full-text search via the `unique-cli search` command. Every invocation wraps each result in a `<sourceN>...</sourceN>` block and records a per-turn citation manifest at `.unique/kb-search-refs.jsonl`, so any fact you cite as `[sourceN]` is rendered with a footnote and a clickable reference chip in the chat UI.

> **Limitation:** Excel (`.xlsx`/`.xls`), CSV (`.csv`), and image files are **not** full-text indexed. They will not appear in search results. To find these files, use the `unique-cli-file-management` skill and browse folders with `unique-cli ls` to locate them by name.


## Basic Search

```bash
# Search across the entire knowledge base
unique-cli search "quarterly revenue analysis"

# Limit results
unique-cli search "budget forecast" --limit 50
```

## Scoped Search

Restrict search to a specific folder:

```bash
# By absolute path
unique-cli search "growth" --folder /Reports/Q1

# By folder name (relative to current dir in interactive mode)
unique-cli search "growth" -f Q1

# By scope ID
unique-cli search "growth" -f scope_abc123
```

When no `--folder` is given:
- In interactive mode: searches within the current directory
- At root `/`: searches the entire knowledge base

## Metadata Filtering

Filter by metadata fields using `--metadata key=value` (repeatable, AND logic):

```bash
# Single filter
unique-cli search "compliance" --metadata department=Legal

# Multiple filters (AND)
unique-cli search "audit" -m department=Legal -m year=2025

# Combined with folder scope
unique-cli search "regulatory" -f /Legal -m year=2025 -l 50
```

## Command Reference

```
unique-cli search <query> [--folder <path|scope_id>] [--metadata <key=value>]... [--limit <N>]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--folder` | `-f` | Current dir | Folder path, name, or scope ID |
| `--metadata` | `-m` | None | Key=value filter (repeatable) |
| `--limit` | `-l` | 200 | Max results |

## Output Format

Each result is rendered as a `<sourceN>...</sourceN>` block. `N` is **1-based**, unique within the current turn, and **continues across multiple `unique-cli search` calls in the same turn** — the first call in a turn starts at `<source1>`, a follow-up call that returns three more results emits `<source4>`, `<source5>`, `<source6>`, and so on.

```
Found 2 result(s):

<source1>
<|document|>annual-report.pdf</|document|>
<|page|>12-13</|page|>
<|info|>cont_abc123</|info|>
...the quarterly revenue analysis shows a 15% increase...
</source1>

<source2>
<|document|>Q1/financials.xlsx</|document|>
<|page|>1</|page|>
<|info|>cont_def456</|info|>
...revenue breakdown by quarter indicates strong growth...
</source2>
```

Each block carries the document title, page range (when known), content ID, and a text snippet. The full chunk metadata (`chunkId`, `url`, `startPage`, `endPage`, ...) is captured in the per-turn manifest and not duplicated on screen.

## Citation Rules

Cite a fact from `unique-cli search` results with `[sourceN]`, where `N` matches the number on the `<sourceN>` block you read it from. The Unique platform's Swappable Intelligence runner converts each `[sourceN]` marker in your final answer into a `<sup>N</sup>` footnote and a clickable reference chip; without `unique-cli search`, KB facts in your answer appear as plain text only, with no footnote and no chip — so this is the only way to make KB citations render correctly on the platform.

```
The company's quarterly revenue rose 15% year over year [source1],
driven by strong growth in the EMEA segment [source2].
```

**Rules** (enforced by the platform's reference post-processor):

1. **`[sourceN]` is for KB results only.** Web results from `unique-cli web-search` use `[websourceN]` instead — never mix the two namespaces.
2. Only cite numbers you saw in the **current** turn's `unique-cli search` output. Numbers from previous turns are stale and will be silently dropped.
3. Write `source` in singular form with the number in digits: `[source1]`, `[source2]` — not `[Source 1]` or `[source one]`.
4. Prefer citing each fact with a single, most-relevant source.
5. Do not invent source numbers for remembered or inferred facts.

## Scripting with Search

```bash
# Search and count results
unique-cli search "policy update" -l 500 | head -1

# Search specific folder with metadata
unique-cli search "Q4 earnings" \
  --folder /Finance/Reports \
  --metadata status=published \
  --metadata year=2025 \
  --limit 100
```

## Prerequisites

Requires these environment variables:

```bash
UNIQUE_USER_ID    # User ID (required)
UNIQUE_COMPANY_ID # Company ID (required)
UNIQUE_API_KEY    # API key — optional on localhost / secured cluster
UNIQUE_APP_ID     # App ID — optional on localhost / secured cluster
```

Install: `pip install unique-sdk`
