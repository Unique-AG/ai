# Crawlers

Web-page readers used by Unique Web Search to fetch URLs and convert them to text.

## Architecture

Crawler configuration lives in **`unique_search_proxy_core.crawlers`**. The tool registers implementations via `CRAWLER_REGISTRY` and dispatches through `BaseCrawler`.

```mermaid
flowchart LR
  Config["proxy-core *Config"]
  Registry["CRAWLER_REGISTRY"]
  Base["BaseCrawler"]
  SDK["SDK crawl"]
  Legacy["_legacy_crawl"]

  Config --> Registry
  Registry --> Base
  Base -->|"SEARCH_PROXY_BASE_URL set"| SDK
  Base -->|"unset"| Legacy
```

### Key invariants

- **No exposable params.** Crawlers have no LLM override surface — only deployment defaults + `urls`.
- **Proxy body = config fields + urls.** `BaseCrawler._proxy_crawl` dumps `config.model_dump(exclude={"crawler", ...})` into the SDK call.
- **Legacy retained** when the search proxy is disabled.

## Available crawlers

| Name | Config source | Auth | Notes |
|------|---------------|------|-------|
| Basic | tool-local `BasicConfig` extends proxy-core | none | HTTP fetch + processors; `content_types` toggles; `url_blocked_patterns` (tool-local, stripped before proxy) |
| Tavily | `TavilyConfig` | `TAVILY_API_KEY` | Extract API |
| Jina | `JinaConfig` | `JINA_API_KEY` | Reader API |
| Firecrawl | `FirecrawlConfig` | `FIRECRAWL_API_KEY`, or the Search Proxy's key | Scrape for one URL, batch scrape for several |

There is **no Crawl4AI** crawler.

A crawler is offered as Web Page Reader when it is listed in `ACTIVE_INHOUSE_CRAWLERS` or its API key is set. A crawler that runs through the Search Proxy needs no key on the assistant: list it, for example `ACTIVE_INHOUSE_CRAWLERS=["basic", "firecrawl"]`.

`WebSearchConfig.crawler_config` is a discriminated union on `crawler` (`Basic` / `Tavily` / `Jina` / `Firecrawl`).

---

## Basic

| Field | Default | Notes |
|-------|---------|-------|
| `timeout` | from base | Per-request timeout (seconds) |
| `content_types` | html/xhtml/plain/markdown on; pdf off | Which MIME types to process |
| `max_concurrent_requests` | `10` | Parallelism |
| `url_blocked_patterns` | tool-local | Regex URL blocklist; **not** sent to the proxy |

```python
from unique_search_proxy_core.crawlers import CrawlerType
from unique_web_search.services.crawlers import BasicConfig, get_crawler_service

config = BasicConfig(crawler=CrawlerType.BASIC, timeout=30)
markdowns = await get_crawler_service(config).crawl(["https://example.com"])
```

---

## Tavily

| Field | Default | Notes |
|-------|---------|-------|
| `extract_depth` | `advanced` | `basic` / `advanced` |
| `format` | `markdown` | `markdown` / `text` |
| `query` | unset | Optional rerank intent |
| `chunks_per_source` | unset | Requires `query` |
| `include_images` / `include_favicon` / `include_usage` | `false` | Response extras |

---

## Jina

| Field | Default | Notes |
|-------|---------|-------|
| `return_format` | `markdown` | `markdown` / `html` / `text` / … |
| `engine` | `browser` | `auto` / `browser` / `direct` / `cf-browser-rendering` |
| `page_timeout` | unset | Seconds; falls back to crawl `timeout` |
| `max_concurrent_requests` | `10` | |
| `no_cache` | `false` | |
| `do_not_track` | `true` | |
| selectors / summaries | unset / false | `target_selector`, `wait_for_selector`, `remove_selector`, image/link options, `locale`, `referer`, `proxy_url` |

---

## Firecrawl

| Field | Default | Notes |
|-------|---------|-------|
| `timeout` | `60` | Seconds. A page that is not in Firecrawl's cache takes 5 to 10 seconds |
| `only_main_content` | `true` | Strip chrome before markdown |
| `only_clean_content` | `false` | Extra LLM clean pass |
| `max_concurrency` | unset | Batch parallelism |
| `ignore_invalid_urls` | `true` | |
| `wait_for` | `0` | ms delay before fetch |
| `mobile` | `false` | |
| `block_ads` | `true` | |
| `remove_base64_images` | `true` | |
| `proxy` | `auto` | Firecrawl proxy tier |
| `max_age` | `600000` | How old Firecrawl's cached copy may be, in milliseconds; `0` reads live. Firecrawl's own default is `172800000` (two days) |
| `store_in_cache` | `true` | `false` keeps the pages out of Firecrawl's cache |
| `max_pdf_pages` | `20` | Firecrawl bills each PDF page; `10000` is its maximum |
| `country` / `languages` | unset | Where and in which languages the pages are read |
| `zero_data_retention` | `false` | Read with zero data retention even when the Search Proxy is deployed without it |
| `include_tags` / `exclude_tags` / `scrape_headers` | unset | Optional |

The direct path (no Search Proxy) sends only the URLs and the timeout to Firecrawl. It cannot send zero data retention, so with `zero_data_retention` on the crawl raises and the web search call fails.

---

## Adding a crawler

1. Define config (+ request model) in `unique_search_proxy_core.crawlers.<name>`.
2. Add a tool module with `@register_crawler(...)` implementing `_legacy_crawl`.
3. Modules are auto-discovered; keep static unions in `__init__.py` and cover with `tests/test_crawler_registry.py`.
