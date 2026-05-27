# Crawler Documentation

This directory contains implementations of the different web crawlers used by `unique_web_search`. Crawlers are responsible for fetching raw page content (usually transformed to Markdown) after the search engines return URLs.

All crawlers inherit from the shared base classes in `base.py`.

### URL safety

Crawlers route every URL through `services/crawlers/url_safety/` before fetching:

- **`BaseCrawler.crawl`** calls `UrlSafetyService.validate_batch_urls` first, then passes `list[ResolvedCrawlTarget]` to each crawler’s `_crawl`. When `url_safety_settings.enabled` is `False`, validation is bypassed and each URL is wrapped via `bypass_crawl_target` without DNS resolution or policy checks.
- **`BasicCrawler`** uses `ResolvedCrawlTarget.request_url`, `host_header`, and `sni_hostname` for DNS pinning (single resolve inside `validate_batch_urls`).
- **`Crawl4AICrawler`** registers a Playwright `before_goto` hook that calls `UrlSafetyService.validate_url` on every navigation when `url_safety_settings.enabled` is `True`.
- **API crawlers** (Tavily, Firecrawl, Jina) use `target.normalized_url` from the validated targets.

Settings live in `url_safety/settings.py` (`url_safety_settings`, env prefix `URL_SAFETY_`). Key fields include `enabled` (`URL_SAFETY_ENABLED`), `resolve_redirects` (`URL_SAFETY_RESOLVE_REDIRECTS`), and the host/scheme allowlists (`allowed_schemes`, `localhost_hosts`, `metadata_hosts`, `cluster_local_suffix`, `service_suffix`).

```python
class BaseCrawlerConfig(BaseModel):
    crawler_type: CrawlerType
    timeout: int = 10  # seconds

class BaseCrawler(ABC):
    async def crawl(self, urls: list[str]) -> list[str]:
        """Return Markdown content for each URL (same ordering as input)."""
```

## Table of Contents

- [Overview](#overview)
- [Crawler Decision Matrix](#crawler-decision-matrix)
- [Crawler Details](#crawler-details)
  - [Basic Crawler](#basic-crawler)
  - [Crawl4AI Crawler](#crawl4ai-crawler)
  - [Tavily Crawler](#tavily-crawler)
  - [Firecrawl Crawler](#firecrawl-crawler)
  - [Jina Crawler](#jina-crawler)
- [Choosing a Crawler](#choosing-a-crawler)
- [Adding a New Crawler](#adding-a-new-crawler)

---

## Overview

| Crawler | Type | Requires API Key | JavaScript Support | Parallelism | Content Quality |
|---------|------|------------------|--------------------|-------------|-----------------|
| Basic | HTTP fetch + Markdownify | No | ❌ | ✅ (configurable) | Depends on page structure |
| Crawl4AI | Headless Chromium | No (uses local browser) | ✅ | ✅ (highly configurable) | High (Markdown + filtering) |
| Tavily | Tavily Extract API | ✅ | ✅ (handled by Tavily) | Batched (20 URLs/request) | High (Markdown) |
| Firecrawl | Firecrawl API | ✅ | ✅ (rendered) | ✅ | High (Markdown) |
| Jina | Jina Reader API | ✅ | ✅ | ✅ | High (Markdown, meta info) |

---

## Crawler Decision Matrix

| Crawler | Best For | JS Rendering | Cost | Setup Complexity |
|---------|----------|--------------|------|------------------|
| **Basic** | Simple HTML pages, no API dependency | No | Free | Low |
| **Crawl4AI** | Complex pages needing browser automation | Yes | Free (local runtime) | Medium (Playwright install) |
| **Tavily** | Fast Markdown extraction with API | Yes | Pay per use | Low |
| **Firecrawl** | Dynamic/SPA heavy content | Yes | Pay per use | Low |
| **Jina** | Clean Markdown + metadata | Yes | Pay per use | Low |

---

## Crawler Details

### Basic Crawler

**File:** `basic.py`  
**Type:** `CrawlerType.BASIC`  
**Authentication:** None  
**When to use:** You want a lightweight crawler without external dependencies.

#### Features
- Asynchronous HTTP fetching using shared proxy-aware client.
- Randomized User-Agent via `fake_useragent`.
- Markdown conversion via `markdownify`.
- URL blacklist (regex) and content-type filtering (skip PDFs, binary files, etc.).
- Configurable concurrency limits.

#### Configuration

```python
from unique_web_search.services.crawlers.basic import BasicCrawler, BasicCrawlerConfig

config = BasicCrawlerConfig(
    crawler_type=CrawlerType.BASIC,
    timeout=15,
    url_pattern_blacklist=[r".*\\.pdf$", r".*download.*"],
    unwanted_content_types={"application/pdf", "image/"},
    max_concurrent_requests=5,
)

crawler = BasicCrawler(config)
markdown_pages = await crawler.crawl(urls)
```

#### Pros / Cons
- ✅ No API keys, easy to run anywhere.
- ✅ Fully controllable (headers, filtering).
- ❌ No JS execution.
- ❌ Quality depends on HTML structure.

---

### Crawl4AI Crawler

**File:** `crawl4ai.py`  
**Type:** `CrawlerType.CRAWL4AI`  
**Authentication:** None (uses local `crawl4ai` runtime)  
**When to use:** You need high-quality Markdown from JS-heavy sites using a headless browser.

#### Features
- Headless Chromium rendering via `crawl4ai`.
- Configurable cache modes and rate limiting.
- Pruning/content filtering to remove boilerplate.
- Full-page scanning, scrolling, overlay removal, navigator spoofing, and user simulation.
- Markdown generation with configurable options (ignore links, emphasis, images, etc.).

#### Requirements
- `crawl4ai` Python package installed.
- Playwright dependencies (Chromium).

#### Configuration

```python
from unique_web_search.services.crawlers.crawl4ai import (
    Crawl4AiCrawler,
    Crawl4AiCrawlerConfig,
    DisplayMode,
)

config = Crawl4AiCrawlerConfig(
    crawler_type=CrawlerType.CRAWL4AI,
    timeout=30,
    max_concurrent_requests=5,
    markdown_generator_config={"options": {"ignore_links": True}},
    rate_limiter_config={"max_retries": 2, "rate_limit_codes": [429, 503]},
    crawler_config={"scan_full_page": True, "wait_until": "networkidle"},
)

crawler = Crawl4AiCrawler(config)
markdown_pages = await crawler.crawl(urls)
```

#### Pros / Cons
- ✅ High fidelity content (JS support).
- ✅ Fine-grained control (cache, rate limiting, pruning).
- ❌ Requires headless browser environment.
- ❌ Higher resource usage than API-based crawlers.

---

### Tavily Crawler

**File:** `tavily.py`  
**Type:** `CrawlerType.TAVILY`  
**Authentication:** `TAVILY_API_KEY`  
**When to use:** You rely on Tavily’s extraction API for consistent Markdown output.

#### Features
- Uses Tavily’s `extract` endpoint (up to 20 URLs per batch).
- Markdown output with `raw_content`.
- Configurable extraction depth (`basic` vs `advanced`).
- Automatic error handling (failed URLs include error messages).

#### Environment Variables

```bash
TAVILY_API_KEY=your_tavily_api_key
```

#### Configuration

```python
from unique_web_search.services.crawlers.tavily import TavilyCrawler, TavilyCrawlerConfig

config = TavilyCrawlerConfig(
    crawler_type=CrawlerType.TAVILY,
    timeout=30,
    depth="advanced",
)

crawler = TavilyCrawler(config)
markdown_pages = await crawler.crawl(urls)
```

#### Pros / Cons
- ✅ High-quality Markdown.
- ✅ Handles JS automatically.
- ❌ Paid API usage.
- ❌ Max 20 URLs per request (batched internally).

---

### Firecrawl Crawler

**File:** `firecrawl.py`  
**Type:** `CrawlerType.FIRECRAWL`  
**Authentication:** `FIRECRAWL_API_KEY`  
**When to use:** You need JS-rendered content or prefer Firecrawl’s scraping pipeline.

#### Features
- Uses Firecrawl’s `batch_scrape` API.
- Markdown output with error fallback.
- Supports multiple output formats (currently Markdown).
- Timeout control via config.

#### Environment Variables

```bash
FIRECRAWL_API_KEY=your_firecrawl_api_key
```

#### Configuration

```python
from unique_web_search.services.crawlers.firecrawl import FirecrawlCrawler, FirecrawlCrawlerConfig

config = FirecrawlCrawlerConfig(
    crawler_type=CrawlerType.FIRECRAWL,
    timeout=45,
)

crawler = FirecrawlCrawler(config)
markdown_pages = await crawler.crawl(urls)
```

#### Pros / Cons
- ✅ JS rendering handled by Firecrawl.
- ✅ Simple configuration.
- ❌ Paid API usage.
- ❌ Dependent on Firecrawl service availability.

---

### Jina Crawler

**File:** `jina.py`  
**Type:** `CrawlerType.JINA`  
**Authentication:** `JINA_API_KEY`  
**When to use:** You need Markdown plus metadata (images, links, etc.) via Jina Reader.

#### Features
- Uses Jina Reader API (via Jina Search settings).
- Returns Markdown content, title, description, images, links.
- Customizable headers (engine, return format).
- Asynchronous HTTP requests with shared timeout.

#### Environment Variables

```bash
JINA_API_KEY=your_jina_api_key
JINA_READER_ENDPOINT=https://r.jina.ai/http://
```

*(Exact reader endpoint depends on your settings; see `client_settings`.)*

#### Configuration

```python
from unique_web_search.services.crawlers.jina import JinaCrawler, JinaCrawlerConfig

config = JinaCrawlerConfig(
    crawler_type=CrawlerType.JINA,
    timeout=20,
    headers={
        "X-Return-Format": "markdown",
        "X-Engine": "browser",
    },
)

crawler = JinaCrawler(config)
markdown_pages = await crawler.crawl(urls)
```

#### Pros / Cons
- ✅ Clean Markdown + metadata.
- ✅ JS rendering supported by Jina backend.
- ❌ Paid API usage.
- ❌ Rate limits apply.

---

## Choosing a Crawler

### Recommendations

- **Use BasicCrawler** if:
  - You have simple static HTML pages.
  - You need a crawler that works offline without API keys.
  - You want full control over headers and filtering.

- **Use Crawl4AiCrawler** if:
  - You need Playwright/Chromium rendering.
  - You want to avoid API costs but can run headless browsers.
  - You need advanced anti-bot/overlay handling.

- **Use Tavily/Firecrawl/Jina Crawlers** if:
  - You prefer managed scraping services.
  - You need quick, reliable Markdown content.
  - You’re okay with API usage costs.

### Mixed Strategies

Many production deployments use multiple crawlers:

- Try Tavily (fast, managed) → fallback to Basic for failures.
- Use Crawl4AI for critical JS-heavy pages, Basic for the rest.
- Allow Custom API search results to reuse the provider’s own extraction.

---

## Adding a New Crawler

1. **Create Config + Crawler**:
   ```python
   class MyCrawlerConfig(BaseCrawlerConfig[CrawlerType.MY]):
       crawler_type: Literal[CrawlerType.MY] = CrawlerType.MY
       api_key: str

   class MyCrawler(BaseCrawler[MyCrawlerConfig]):
       async def crawl(self, urls: list[str]) -> list[str]:
           # Implement crawling logic
           return markdown_contents
   ```

2. **Register Crawler Type**:
   - Add to `CrawlerType` enum.
   - Expose via factory in `crawlers/__init__.py`.

3. **Update Tests & Docs**:
   - Add unit tests.
   - Document configuration and usage.

---

## Error Handling Best Practices

- **Per-URL errors**: Return friendly error messages (not exceptions) to keep ordering intact.
- **Timeouts**: Use `config.timeout` to prevent long-running requests.
- **Concurrency**: Respect API limits (Tavily/Firecrawl/Jina have rate limits).
- **Retries**: Implement or rely on API-side retries for temporary failures.

---

## Performance Tips

- Use BasicCrawler for bulk crawling when JS isn’t required.
- Use Crawl4AI when you control the infrastructure and need high fidelity.
- Leverage Tavily/Firecrawl/Jina for quality + speed with minimal setup.
- Mix crawlers using a fallback mechanism for resilience.

---

Happy crawling! 🕷️


