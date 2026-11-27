# Unique Web Search

Configurable web search tool for Unique assistants: search the web, read pages, and return citation-ready content chunks.

## Search Proxy (recommended)

Outbound web access should go through **Unique Search Proxy** (`connectors/unique_search_proxy/`). When `SEARCH_PROXY_BASE_URL` is set, search and crawl calls use `unique-search-proxy-sdk`; credentials and provider egress stay on the proxy pod.

| Mode | When | Behaviour |
|------|------|-----------|
| **Proxy (recommended)** | `SEARCH_PROXY_BASE_URL` set | `_proxy_search` / `_proxy_crawl` via the SDK |
| **Legacy** | URL unset | Direct provider calls from this process (`_legacy_search` / `_legacy_crawl`) |

- **New standard engines (Brave, Perplexity, Firecrawl) are proxy-only** — legacy raises.
- **Custom API** uses proxy egress only when
  `FEATURE_FLAG_SEARCH_PROXY_ENABLE_CUSTOM_API_UN_26736` is enabled; otherwise
  the legacy path reports URL-safety outcomes without blocking.
- Future provider work targets Search Proxy only; legacy is preserved for migrated engines.

Packages involved: [`unique-search-proxy-core`](../../connectors/unique_search_proxy/unique_search_proxy_core/README.md) (schemas), [`unique-search-proxy-sdk`](../../connectors/unique_search_proxy/unique_search_proxy_sdk/README.md) (HTTP), [`unique-search-proxy`](../../connectors/unique_search_proxy/unique_search_proxy_client/README.md) (server). System overview: [`connectors/unique_search_proxy/README.md`](../../connectors/unique_search_proxy/README.md).

## Architecture

![Web Search Tool Architecture](docs/images/architecture-diagram.svg)

## Search engine kinds

### Standard search

Query → normalised results (URL / title / snippet / optional content). Optional page crawl via the configured crawler.

| Engine | Proxy | Notes |
|--------|-------|-------|
| Google | legacy + proxy | Requires scraping by default |
| Brave | **proxy-only** | Rich snippets; configurable `requires_scraping` (on by default); `ExposableParam` knobs |
| Perplexity | **proxy-only** | Content extraction knobs; configurable `requires_scraping` (on by default); `ExposableParam` |
| Firecrawl | **proxy-only** | `requires_scraping` (default off; when on, the Web Page Reader reads the pages); `scrape_results` lets Firecrawl read the pages inside the search call instead; `ExposableParam` |
| Custom API | legacy + proxy | Your REST endpoint; proxy mode rejects redirects |

Standard engines that live in proxy-core use **`ExposableParam`** (`expose` + `value`) for optional provider knobs. See [Search Engines README](./src/unique_web_search/services/search_engine/README.md).

### Agent search (grounding)

An upstream AI agent / grounded model searches and returns opaque text that this tool parses into `WebSearchResult`s. Bing results take their URLs only from the citations Foundry attaches to the answer, never from the answer text.

| Engine | Proxy | Notes |
|--------|-------|-------|
| Bing (Azure AI Foundry grounding) | legacy + proxy | Configurable `requires_scraping`; fixed `market` / `freshness` chosen by an admin, with `market` falling back to `BING_AGENT_DEFAULT_MARKET` |
| VertexAI (Gemini grounding) | legacy + proxy | Configurable `requires_scraping` |

Bing's grounding knobs are baked into the hashed Foundry agent name, so changing
one provisions a new agent version.

## Web crawlers (page readers)

| Crawler | Auth | Notes |
|---------|------|-------|
| Basic | none | HTTP + content-type toggles; tool-local `url_blocked_patterns` (legacy) |
| Tavily | `TAVILY_API_KEY` | Extract API |
| Jina | `JINA_API_KEY` | Reader API |
| Firecrawl | `FIRECRAWL_API_KEY`, or the Search Proxy's key | Scrape (one URL) or batch scrape (several) |

No Crawl4AI. Crawler configs have **no exposable LLM knobs**.

## Execution modes

| Mode | Status | Behaviour |
|------|--------|-----------|
| **V1** | Stable | Refine query → search → crawl → process |
| **V2** | Stable | Parallel plan steps (search / read URL) |
| **V3** | Experimental | Agent loop: snippet `search` vs on-demand `read_urls` |

Proxy vs legacy is transparent to executors.

## Detailed subsystem docs

- [Search Engines](./src/unique_web_search/services/search_engine/README.md)
- [Crawlers](./src/unique_web_search/services/crawlers/README.md)
- [Executors](./src/unique_web_search/services/executors/README.md)

## Activity Records

Records are written only when the host runs the activity records outbox and both `FEATURE_FLAG_ENABLE_WEB_SEARCH_ACTIVITY_RECORDS_UN_28965` and `FEATURE_FLAG_ENABLE_ACTIVITY_RECORDS_EVENTS_UN_22616` are on. `..._UN_28965` is evaluated for the company and the user, so a user-level rule applies. `..._UN_22616` is evaluated for the company only. Delivery is best effort: a failed enqueue is logged and the search carries on. A successful call that sent no query emits no record.

If `..._UN_28965` is on but no outbox is running, each tool call increments `unique_activity_event_outbox_record_failures_total` and one warning is logged per process.

With that in place, each tool call emits one `web-search.query.sent` per outgoing query, or one `web-search.tool.denied` / `web-search.tool.failed` when it sent no query. The `criticalData` keys are defined as TypedDicts in [`activity_record.py`](./src/unique_web_search/activity_record.py):

| Key | Records | Content |
|-----|---------|---------|
| `chatId`, `messageId`, `toolCallId` | all | Where the call happened |
| `userPrompt` | all | User message, cut at 4096 characters |
| `userPromptTruncated` | all, optional | `true` when `userPrompt` was cut |
| `args` | all | Validated tool parameters, or the raw arguments if validation failed |
| `argumentScreening` | all | `status` (`notRun`, `approved`, `rejected`) and `reason` |
| `elicitation` | all | `status` and `proposedQueries` |
| `query` | `query.sent` | The query sent to the engine |
| `params` | `query.sent` | Exposed provider parameters, `null` when there are none |
| `egress` | `query.sent` | `viaSearchProxy`, `endpoint` origin, optional `destination` origin |
| `responseReceived` | `query.sent` | Whether the engine answered, error status included |
| `error` | `query.sent`, optional | Exception class name when the search raised |
| `reason` | `denied` / `failed`, optional | Exception class name, or `ArgumentScreeningBlocked` |

## Configuration

- `SEARCH_PROXY_BASE_URL` — enables the Search Proxy client
- Provider API keys (on the proxy pod when proxy is enabled; otherwise on assistants-core for legacy)
- Search / crawler / content-processing settings via `WebSearchConfig`

## Dependency management (uv.lock + min/latest testing)

This package is a **library** and uses `uv` for dependency management.

We run tests additionally with minimal dependencies to ensure that the listed ranges are valid. NOTE: We use lowest-direct, not lowest.
Lowest attempts to use the lowest possible dependency versions _transitively_ causing issues if a dependency has incorrect metadata. Example:
- google-cloud-aiplatform says it works with shapely<3.0.0.
- The lowest resolver assumes 1.0 which needs python 2 -> breaks
Therefore we use lowest-direct which only sets our direct dependencies to lowest. However, this only correctly verifies our min dependencies
if our code correctly lists all the required dependencies and never imports a transitive dependency. We therefore use deptry to ensure we
don't use transitive dependencies and that we have no unused dependencies.

### Test locally

- **Latest deps and deptry**:

```bash
cd tool_packages/unique_web_search
uv sync
uv run pytest
uv run deptry
```

- **Min deps**:

```bash
cd tool_packages/unique_web_search
uv venv
uv pip install -e . --resolution=lowest-direct
uv export --only-group dev --no-hashes | uv pip install -r -
uv run --no-sync pytest
```
