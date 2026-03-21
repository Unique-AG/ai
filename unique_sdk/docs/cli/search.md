# Search Guide

!!! warning "Experimental"
    The CLI is experimental and its interface may change in future releases.

The `search` command uses the Unique platform's **combined search** (vector + full-text) to find relevant content across the knowledge base. It is the one command that goes beyond typical filesystem operations, providing semantic search capabilities.

## Basic Usage

```
search <query>
```

By default, search looks in the current directory (and its scope) with a limit of 200 results:

```
/Reports> search "quarterly revenue analysis"
Found 15 result(s):

    1. annual-report.pdf (p.12-13)  [cont_abc123]
       ...the quarterly revenue analysis shows a 15% increase...
    2. Q1/financials.xlsx (p.1)  [cont_def456]
       ...revenue breakdown by quarter indicates strong growth...
```

## Restricting by Folder

Use `--folder` (or `-f`) to search within a specific folder. The folder can be specified as a path, a relative name, or a scope ID:

```
# By absolute path
search "growth" --folder /Company/Reports/Q1

# By relative name (resolved from current directory)
search "growth" --folder Q1

# By scope ID
search "growth" --folder scope_abc123
```

When no `--folder` is given and you are inside a folder (not at root), the search is scoped to the current directory.

When at root `/`, no folder filter is applied and the search spans the entire knowledge base.

## Filtering by Metadata

Use `--metadata` (or `-m`) to add metadata filters. Each filter is a `key=value` pair. Multiple filters are combined with AND logic:

```
# Single filter
search "compliance" --metadata department=Legal

# Multiple filters (AND)
search "audit" --metadata department=Legal --metadata year=2025
```

Under the hood, each `--metadata key=value` creates a UniqueQL `EQUALS` filter on the metadata field `key`.

### How Folder Filtering Works Internally

When you specify a folder, the CLI builds a metadata filter on the `folderIdPath` field using the `uniquepathid://` scheme:

```python
{
    "path": ["folderIdPath"],
    "operator": "contains",
    "value": "uniquepathid://scope_abc123"
}
```

If you also supply `--metadata` filters, they are combined with the folder filter using AND:

```python
{
    "and": [
        {"path": ["folderIdPath"], "operator": "contains", "value": "uniquepathid://scope_abc123"},
        {"path": ["department"], "operator": "equals", "value": "Legal"},
        {"path": ["year"], "operator": "equals", "value": "2025"}
    ]
}
```

## Controlling Result Count

The default limit is 200 results. Use `--limit` (or `-l`) to change this:

```
search "strategy" --limit 50
search "all documents" --limit 500
```

## Output Format

Each result shows:

1. **Index** -- numbered position in the result list
2. **Title** -- file name or document title
3. **Pages** -- the page range where the match was found (e.g., `p.5-6`)
4. **Content ID** -- the unique identifier in brackets
5. **Snippet** -- a text excerpt from the matching chunk (first 120 characters)

```
    1. annual-report.pdf (p.5-6)  [cont_abc123]
       ...revenue growth exceeded expectations across all business segments...
    2. Q1/summary.docx (p.2)  [cont_def456]
       ...growth metrics indicate strong revenue trajectory for the year...
```

## One-Shot Examples

```bash
# Search everything
unique-cli search "AI roadmap"

# Search in a specific folder
unique-cli search "budget" --folder /Finance/2025

# Search with metadata filter and custom limit
unique-cli search "regulatory changes" -f /Legal -m year=2025 -l 50

# Combine multiple metadata filters
unique-cli search "quarterly" -m department=Finance -m status=published
```

## Technical Details

- **Search type**: Always `COMBINED` (vector similarity + full-text keyword matching, results merged and ranked)
- **Scope filtering**: When a folder is specified, its scope ID is passed as `scopeIds` to the Search API
- **Metadata filtering**: Built using [UniqueQL](../uniqueql.md) operators (`EQUALS` for `--metadata`, `CONTAINS` for folder path)
- **Default limit**: 200 results
