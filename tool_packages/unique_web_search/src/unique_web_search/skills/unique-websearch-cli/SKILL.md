---
name: unique-websearch-cli
description: >-
  Two-phase web search CLI: `search` returns URLs with snippets,
  `crawl` fetches full page content for selected URLs. Designed
  for AI-assisted workflows where a model selects which pages to
  fetch after reviewing search snippets.
---

# Unique WebSearch CLI

Two-phase web search from the terminal. Phase 1 queries a search
engine for URLs and snippets. Phase 2 crawls selected URLs to
retrieve full page content. This separation lets an AI decide which
pages are worth fetching before spending time on crawling.

## Setup

### 1. Environment variables (required)

Set which search engine to use and provide its API keys:

```bash
# Engine selection (default: google)
export ACTIVE_SEARCH_ENGINES='["google"]'

# Crawler selection (default: basic, crawl4ai)
export ACTIVE_INHOUSE_CRAWLERS='["basic", "crawl4ai"]'
```

Then set the API keys for your configured engine:

**Google:**
```bash
export GOOGLE_SEARCH_API_KEY="..."
export GOOGLE_SEARCH_ENGINE_ID="..."
export GOOGLE_SEARCH_API_ENDPOINT="https://www.googleapis.com/customsearch/v1"
```

**Brave:**
```bash
export BRAVE_SEARCH_API_KEY="..."
export BRAVE_SEARCH_API_ENDPOINT="https://api.search.brave.com/res/v1/web/search"
```

**Tavily:**
```bash
export TAVILY_API_KEY="..."
```

**Jina:**
```bash
export JINA_API_KEY="..."
```

**Firecrawl:**
```bash
export FIRECRAWL_API_KEY="..."
```

### 2. Optional config file

Create `~/.unique-websearch.json` to override non-secret settings like
`fetch_size` or crawler `timeout`. The engine and crawler selection still
comes from environment variables — the JSON file only tunes their settings.

```json
{
  "search_engine_config": { "fetch_size": 50 },
  "crawler_config": { "timeout": 15 }
}
```

Override the path with `--config` or the `UNIQUE_WEBSEARCH_CONFIG` env var.
If no config file exists, defaults are used (fetch_size: 50, timeout: 10).

## Usage

### Phase 1 — Search

Get URLs and snippets from the configured search engine:

```bash
unique-websearch search "quarterly earnings report 2025"
unique-websearch search "AI regulation EU" -n 10
unique-websearch search "python tutorial" --json
```

JSON output for piping to other tools:

```bash
unique-websearch search "query" --json | jq '.[].url'
```

### Phase 2 — Crawl

Fetch full page content for specific URLs:

```bash
unique-websearch crawl https://example.com https://other.com
unique-websearch crawl --parallel 5 https://a.com https://b.com
```

Pipe URLs from search results:

```bash
unique-websearch search "query" --json | jq -r '.[].url' | unique-websearch crawl --stdin
```

## Command Reference

### `unique-websearch search <query>`

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--fetch-size` | `-n` | 50 (or from config) | Number of results to fetch |
| `--json` | | Off | Output as JSON array |
| `--config` | `-c` | `~/.unique-websearch.json` | Config file path |

### `unique-websearch crawl <url>...`

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--parallel` | `-p` | 10 | URLs to crawl concurrently per batch |
| `--stdin` | | Off | Read URLs from stdin (one per line) |
| `--json` | | Off | Output as JSON array |
| `--config` | `-c` | `~/.unique-websearch.json` | Config file path |

### Global options

| Option | Short | Description |
|--------|-------|-------------|
| `--config` | `-c` | Config file path |
| `--version` | | Show version |
| `--help` | | Show help |

## Output Format

### Search (text)
```
Found 3 result(s):

  1. Example Page Title
     https://example.com/article
     A short snippet describing the content found on this page...

  2. Another Relevant Result
     https://another.com/page
     More details about the search query topic...
```

### Search (JSON)
```json
[
  {
    "title": "Example Page Title",
    "url": "https://example.com/article",
    "snippet": "A short snippet describing the content..."
  }
]
```

### Crawl (text)
```
Crawled 2 URL(s):

  1. https://example.com/article
     [4523 chars]
     Full page content preview truncated to 500 characters...

  2. https://other.com/page
     [2891 chars]
     Another page's content preview...
```

### Crawl (JSON)
```json
[
  {
    "url": "https://example.com/article",
    "content": "Full page content as markdown...",
    "error": null
  }
]
```

## Two-Phase Workflow for AI Agents

1. Run `unique-websearch search "<query>" --json` to get candidate URLs.
2. The AI reviews the titles and snippets to decide which URLs are relevant.
3. Run `unique-websearch crawl <selected-urls>` to get full content.
4. The AI processes the full page content.

## Install

```bash
pip install unique-web-search
```
