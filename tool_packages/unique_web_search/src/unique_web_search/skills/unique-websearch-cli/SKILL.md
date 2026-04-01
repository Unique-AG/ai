---
name: unique-websearch-cli
description: >-
  Search the web using the unique-websearch command-line tool. Use when
  the user asks to search the public web, find web pages, or look up
  information online using Google, Brave, Tavily, or other supported
  search engines. Results include URLs, snippets, and optionally
  crawled page content.
---

# Unique WebSearch CLI

Search the public web from the terminal using configurable search engines
via the `unique-websearch` command.

## Setup

### 1. Config file

Create `~/.unique-websearch.json` with your engine and crawler settings:

```json
{
  "search_engine_config": {
    "search_engine_name": "Google",
    "fetch_size": 5
  },
  "crawler_config": {
    "crawler_type": "BasicCrawler",
    "timeout": 10
  }
}
```

Override the path with `--config` or the `UNIQUE_WEBSEARCH_CONFIG` env var.

### 2. Environment variables

Set API keys for your chosen search engine:

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

## Basic Usage

```bash
# Search with defaults from config
unique-websearch "quarterly earnings report 2025"

# Control number of results
unique-websearch "AI regulation EU" -n 10

# Fast mode -- URLs and snippets only, no page crawling
unique-websearch "python asyncio tutorial" --no-crawl
```

## Override Search Engine

```bash
# Use Brave instead of the configured engine
unique-websearch "climate change policy" --engine brave -n 8

# Use Tavily (returns content directly, no crawling needed)
unique-websearch "latest OpenAI announcements" -e tavily
```

## Command Reference

```
unique-websearch <query> [options]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--fetch-size` | `-n` | From config | Number of results to fetch |
| `--engine` | `-e` | From config | Override search engine |
| `--no-crawl` | | Off | Skip page crawling |
| `--config` | `-c` | `~/.unique-websearch.json` | Config file path |
| `--version` | | | Show version |
| `--help` | | | Show help |

## Supported Engines

| Engine | Config name | Requires crawling |
|--------|-------------|-------------------|
| Google | `Google` | Yes |
| Brave | `Brave` | Yes |
| Tavily | `Tavily` | No |
| Jina | `Jina` | No |
| Firecrawl | `Firecrawl` | Depends |
| VertexAI | `VertexAI` | Yes |
| Custom API | `CustomAPI` | Depends |

## Supported Crawlers

| Crawler | Config name |
|---------|-------------|
| Basic HTTP | `BasicCrawler` |
| Crawl4AI | `Crawl4AiCrawler` |
| Tavily | `TavilyCrawler` |
| Firecrawl | `FirecrawlCrawler` |
| Jina | `JinaCrawler` |

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

## Install

```bash
pip install unique-web-search
```
