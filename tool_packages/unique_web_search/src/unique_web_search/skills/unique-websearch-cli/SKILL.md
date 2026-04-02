---
name: unique-websearch-cli
description: >-
  Search the web using the unique-websearch command-line tool. Use when
  the user asks to search the public web, find web pages, or look up
  information online. The search engine and crawler are determined by
  environment variables -- the CLI always uses whichever single engine
  and crawler are configured, not a choice of all engines.
---

# Unique WebSearch CLI

Search the public web from the terminal. The search engine and crawler
are **automatically determined** from environment variables, matching the
server-side configuration. You do not choose the engine at invocation
time -- it is always the one that is configured.

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
comes from environment variables -- the JSON file only tunes their settings.

```json
{
  "search_engine_config": { "fetch_size": 50 },
  "crawler_config": { "timeout": 15 }
}
```

Override the path with `--config` or the `UNIQUE_WEBSEARCH_CONFIG` env var.
If no config file exists, defaults are used (fetch_size: 50, timeout: 10).

## Usage

```bash
# Search with defaults (50 results, auto-configured engine + crawler)
unique-websearch "quarterly earnings report 2025"

# Control number of results
unique-websearch "AI regulation EU" -n 10

# Fast mode -- URLs and snippets only, no page crawling
unique-websearch "python asyncio tutorial" --no-crawl

# Use a project-specific config file
unique-websearch "internal docs" --config ./project.json
```

## Command Reference

```
unique-websearch <query> [options]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--fetch-size` | `-n` | 50 (or from config) | Number of results to fetch |
| `--no-crawl` | | Off | Skip page crawling |
| `--config` | `-c` | `~/.unique-websearch.json` | Config file path |
| `--version` | | | Show version |
| `--help` | | | Show help |

## Output Format

```
Found 3 result(s):

  1. Example Page Title
     https://example.com/article
     A short snippet describing the content found on this page...

  2. Another Relevant Result
     https://another.com/page
     More details about the search query topic...
     --- crawled content ---
     Full page content preview truncated to 200 characters...
```

## How It Works

1. The CLI reads `ACTIVE_SEARCH_ENGINES` to determine which single search
   engine to use (e.g. Google, Brave, Tavily).
2. The CLI reads `ACTIVE_INHOUSE_CRAWLERS` (plus API keys) to determine
   the active crawler for fetching full page content.
3. An optional JSON config file can override settings like `fetch_size`.
4. The `--fetch-size` / `-n` flag overrides `fetch_size` per invocation.
5. If the engine requires page scraping and `--no-crawl` is not set,
   the first active crawler fetches full page content automatically.

## Install

```bash
pip install unique-web-search
```
