---
name: unique-cli-search
description: >-
  Search the Unique AI Platform knowledge base using the unique-cli search
  command. Use when the user asks to find, search, or query documents
  or content on Unique, including filtering by folder or metadata.
  Also use to read all indexed text chunks of a specific file by its
  content ID (cont_*) using --content-id, without downloading the binary.
  NOTE: Excel/CSV/image files are not full-text indexed — use
  unique-cli-file-management to locate them by name.
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

## Read All Chunks of a Specific File

To retrieve every indexed text chunk for a file whose content ID you already know
(e.g. from a prior `unique-cli ls` or search result), use `--content-id`.
This is faster and complete — it does **not** download the binary file.

```bash
# All chunks for one file
unique-cli search "" --content-id cont_abc123

# Chunks for multiple files in one call
unique-cli search "" --content-id cont_abc123 --content-id cont_def456

# Combined with a limit
unique-cli search "" --content-id cont_abc123 --limit 50
```

Use this instead of `unique-cli download` when you need the document text but
not the original file bytes. Particularly useful when iterating over a known
set of files (e.g. all SOW documents, all KYC forms for a client).

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
unique-cli search <query> [--folder <path|scope_id>] [--metadata <key=value>]...
                          [--limit <N>] [--content-id <cont_*>]...
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--folder` | `-f` | Current dir | Folder path, name, or scope ID |
| `--metadata` | `-m` | None | Key=value filter (repeatable) |
| `--limit` | `-l` | 200 | Max results |
| `--content-id` | `-i` | None | Fetch all chunks for a file ID (repeatable) |

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
UNIQUE_USER_ID    # User ID (required)
UNIQUE_COMPANY_ID # Company ID (required)
UNIQUE_API_KEY    # API key — optional on localhost / secured cluster
UNIQUE_APP_ID     # App ID — optional on localhost / secured cluster
```

Install: `pip install unique-sdk`
