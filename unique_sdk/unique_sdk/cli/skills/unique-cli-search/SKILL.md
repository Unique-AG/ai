---
name: unique-cli-search
description: >-
  Search the Unique AI Platform knowledge base using the unique-cli search
  command. Use when the user asks to find, search, or query documents
  or content on Unique, including filtering by folder or metadata.
  NOTE: This search uses combined vector + full-text indexing. Excel
  (.xlsx/.xls), CSV (.csv), and image files are NOT full-text indexed,
  so they will not appear in search results. To locate these file types,
  use the unique-cli-file-management skill instead (browse folders with
  `unique-cli ls` to find them by name).
---

# Unique CLI -- Knowledge Base Search

Search the Unique knowledge base using combined vector + full-text search via the `unique-cli search` command.

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

## When Global Search Returns No Results

Global (unscoped) search may return 0 results even when matching documents exist,
because documents are indexed under specific folder scopes. If a global search
returns nothing:

1. List root folders to understand the structure:
   ```bash
   unique-cli ls
   ```
2. Re-run the search scoped to the most relevant folder:
   ```bash
   unique-cli search "term" --folder /FolderName
   ```
3. Use a broad single word grounded in a folder name or document type the user mentioned.

**Always prefer folder-scoped search** when the user names a topic, report type, or
folder. Folder-scoped search is more reliable than global search.

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

```
Found 15 result(s):

    1. annual-report.pdf (p.12-13)  [cont_abc123]
       ...the quarterly revenue analysis shows a 15% increase...
    2. Q1/financials.xlsx (p.1)  [cont_def456]
       ...revenue breakdown by quarter indicates strong growth...
```

Each result shows: index, title, page range, content ID, and a text snippet.

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
UNIQUE_API_KEY    # API key (ukey_...)
UNIQUE_APP_ID     # App ID (app_...)
UNIQUE_USER_ID    # User ID
UNIQUE_COMPANY_ID # Company ID
```

Install: `pip install unique-sdk`
