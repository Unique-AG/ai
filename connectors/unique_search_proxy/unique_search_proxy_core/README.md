# unique-search-proxy-core

Part of [Unique Search Proxy](../README.md) · PyPI: `unique-search-proxy-core`

---

## 1. What this package is

**Core is the contract layer.** It defines every shared type — deployment configs, HTTP request/response shapes, error codes, and LLM tool schemas — without importing FastAPI, httpx pools, or provider SDKs.

Install it anywhere you need to **describe** or **validate** proxy behaviour: the proxy server, the HTTP SDK, assistants-core tool manifests, deployment UIs.

| Package | Question it answers |
|---------|---------------------|
| **Core** (this) | *What* can be configured and *what* does a valid request/response look like? |
| [Client](../unique_search_proxy_client/README.md) | *How* are provider calls executed at runtime? |
| [SDK](../unique_search_proxy_sdk/README.md) | *How* do callers reach the proxy over HTTP? |

---

## 2. Role in the system

Core sits at the centre of **Path A** (schema & config). It is imported by both the proxy pod and caller services; it never makes HTTP calls itself.

```mermaid
flowchart TB
    subgraph consumers["Consumers of core"]
        Client["unique_search_proxy_client"]
        SDK["unique_search_proxy_sdk"]
        AC["assistants-core / deployment UI"]
    end

    subgraph core["unique_search_proxy_core"]
        Contracts["Response & error models"]
        Config["*Config deployment models"]
        Project["ConfigRequestResolver\n(request / call-schema / merge)"]
    end

    AC --> Config
    AC --> Project
    Client --> Contracts
    Client --> Config
    SDK --> Contracts
    Project -->|"flat request body"| SDK
    Project -->|"flat request body"| Client
```

System overview → [../README.md](../README.md)

---

## 3. Key concepts

Core uses **three different config patterns** depending on provider kind. Only search engines use `ExposableParam` and the full projection pipeline.

### 3.1 Three provider patterns (search vs agent vs crawl)

All three kinds share one owner — `param_policy.resolver.ConfigRequestResolver` — which derives the request model (leading `query`/`urls` injected via `SearchRequestBase`/`AgentRequestBase`/`CrawlRequestBase`), resolves `ExposableParam` values, and projects the LLM call schema. Search-engine-specific operations (runtime merge, provider query string) live on `BaseSearchEngineConfig`.

| Kind | Config → request | `ExposableParam` | LLM call schema | Config/invocation merge |
|------|------------------|------------------|-----------------|-------------------------|
| **Search engines** | `GoogleConfig` → `GoogleSearchRequest` via `ConfigRequestResolver.request_model` | Yes | `ConfigRequestResolver.call_schema` | `BaseSearchEngineConfig.merge` |
| **Agent engines** | `BingAgentConfig` → `BingAgentSearchRequest` via `ConfigRequestResolver.agent_request_model` | No (plain fields) | Not implemented in core | Not implemented in core |
| **Crawlers** | `BasicConfig` → `BasicCrawlRequest` via `ConfigRequestResolver.crawl_request_model` | No | Not implemented in core | `merge_crawler_config_and_invocation` |

```mermaid
flowchart TB
    subgraph resolver["param_policy/resolver.py — ConfigRequestResolver"]
        RM["request_model / agent_request_model / crawl_request_model"]
        CS["call_schema"]
        MG["resolve_values"]
    end

    subgraph search["Search engines"]
        GC["GoogleConfig\n(ExposableParam knobs)"]
        GSR["GoogleSearchRequest"]
        LLM["LLM call schema"]
        GC --> RM --> GSR
        GC --> CS --> LLM
    end

    subgraph agent["Agent engines"]
        BC["BingAgentConfig\n(plain fields)"]
        BSR["BingAgentSearchRequest"]
        BC --> RM --> BSR
    end

    subgraph crawl["Crawlers"]
        BCrawl["BasicConfig\n(no urls)"]
        BCR["BasicCrawlRequest\n(urls injected)"]
        BCrawl --> RM --> BCR
    end
```

### 3.2 Search engines — three surfaces from one config

Search is the only kind where a single `*Config` fans out into three derived surfaces:

| Surface | Audience | Example |
|---------|----------|---------|
| **Deployment config** | Admin / deployment UI | `{ "engine": "google", "gl": { "expose": true, "value": "de" }, … }` |
| **LLM call schema** | Tool manifest shown to the model | `{ "query", "gl" }` — only fields where `expose: true` |
| **HTTP request body** | `POST /v1/search` wire format | `{ "engine": "google", "query": "…", "gl": "de", "fetchSize": 10 }` |

`ConfigRequestResolver` derives the latter two from the first. Every kind builds its request model the same way: config fields (with `ExposableParam[T]` unwrapped to plain `T`) plus the required leading field (`query` for search/agent, `urls` for crawl) supplied by the shared request base classes.

### 3.3 ExposableParam — search-engine only

Optional **search** parameters use `ExposableParam[T]`:

- **`value`** — admin default merged into every request (`null` = deactivated)
- **`expose`** — when `true`, the parameter appears on the LLM call schema

```python
gl: ExposableParam[str | None] = ExposableParam(expose=False, value="de")  # admin-fixed
gl: ExposableParam[str | None] = ExposableParam(expose=True, value=None)   # LLM-overridable
```

No agent or crawler schema imports `ExposableParam` today.

### 3.4 BaseSearchEngineConfig.merge — search-engine only

```python
from unique_search_proxy_core.search_engines.base import BaseSearchEngineConfig

request = BaseSearchEngineConfig.merge(google_config, {}, query="EU AI Act")
# → validated GoogleSearchRequest ready for POST /v1/search
```

The proxy receives a flat body; it does not resolve deployment config over HTTP.

### 3.5 merge_crawler_config_and_invocation — crawler only

```python
from unique_search_proxy_core.crawlers import merge_crawler_config_and_invocation

request = merge_crawler_config_and_invocation(basic_config, {"urls": ["https://example.com"]})
# → validated BasicCrawlRequest ready for POST /v1/crawl
```

---

## 4. Architecture (modules)

```mermaid
flowchart TB
    subgraph core_pkg["unique_search_proxy_core"]
        Schema["schema.py"]
        Errors["errors.py"]
        PP["param_policy/\nExposableParam + annotations + resolver"]
        Prov["providers/schema.py"]
        SE["search_engines/"]
        AE["agent_engines/"]
        CR["crawlers/"]
    end

    PP --> SE
    PP --> AE
    PP --> CR
    Prov --> SE
    Prov --> CR
    SE --> Schema
    AE --> Schema
    CR --> Schema
    Errors --> Schema
```

| Module | Responsibility |
|--------|----------------|
| `schema.py` | Shared API models: `SearchResponse`, `AgentSearchResponse`, `CrawlResponse`, `WebSearchResult`, `ErrorResponse`, SSE events |
| `errors.py` | `ProxyError` hierarchy and stable `ProxyErrorCode` enum |
| `param_policy/` | `ExposableParam` policy, `annotations.py` (annotation plumbing: `plain_inner_type`/`as_optional`/`as_required`, `field_definition_from_info`, `resolve_field_name`), `field_plan.py` (single per-config field walk), **plus** `resolver.ConfigRequestResolver` — the single owner of config → request/call-schema/value resolution for all three kinds |
| `providers/schema.py` | JSON Schema + defaults for deployment UIs (`provider_config_json_schema`, …) |
| `search_engines/` | Config models (with per-config `provider_param_exclude_fields` override), request union, call-schema resolution |
| `agent_engines/` | Agent config/request models, output schema |
| `crawlers/` | `*Config` deployment models + derived `*CrawlRequest` HTTP bodies |

---

## 5. Provider contracts

Core registers the **discriminator ids** and config models. Runtime registration of service classes lives in the [client](../unique_search_proxy_client/README.md).

| Kind | IDs | Config model |
|------|-----|--------------|
| Search engines | `google`, `brave`, `perplexity` | `GoogleConfig`, `BraveConfig`, `PerplexityConfig` |
| Agent engines | `bing`, `vertexai` | `BingAgentConfig`, `VertexAIAgentConfig` |
| Crawlers | `Basic`, `Tavily`, `Jina`, `Firecrawl` | `BasicConfig`, `TavilyConfig`, … → `BasicCrawlRequest`, … |

Search engines share `BaseSearchEngineConfig` (`fetch_size`, `timeout`). Crawlers share `BaseCrawlerConfig` (`timeout` only — `urls` live on derived request models).

---

## 6. Key APIs (by use case)

### Deployment UI — JSON Schema for a provider

```python
from unique_search_proxy_core.providers.schema import (
    provider_config_json_schema,
    provider_default_config,
)

schema = provider_config_json_schema("search_engine", "google")
defaults = provider_default_config("search_engine", "google")
```

### Tool manifest — LLM call schema

```python
from unique_search_proxy_core.param_policy.resolver import ConfigRequestResolver

projected = ConfigRequestResolver.call_schema(google_config, strict=False)
call_schema = projected.model_json_schema()  # JSON Schema for the LLM tool
```

### Runtime — build flat request before HTTP call

```python
from unique_search_proxy_core.search_engines.base import BaseSearchEngineConfig

body = BaseSearchEngineConfig.merge(config, llm_invocation_dict, query="EU AI Act")
```

### Shared types and errors

```python
from unique_search_proxy_core import (
    SearchResponse,
    ProxyError,
    EngineNotConfiguredError,
    WebSearchResult,
)
```

---

## 7. Features summary

- Discriminated provider configs (`engine`, `crawler` Literal discriminators)
- One resolver (`ConfigRequestResolver`) owns config → request/call-schema/value resolution for all kinds
- **Search-only:** `ExposableParam` policy, three-surface projection, LLM call schema
- **Agent:** config → request derivation via `ConfigRequestResolver.agent_request_model`
- **Crawl:** `ConfigRequestResolver.crawl_request_model` (injects `urls`); `merge_crawler_config_and_invocation`
- **Search runtime merge / provider query string:** `BaseSearchEngineConfig.merge` / `BaseSearchEngineConfig.provider_query_params`
- CamelCase JSON aliases on all models
- Zero server dependencies (import-linter enforced in the client package)

---

## 8. Installation & development

```bash
cd unique_search_proxy_core
uv sync
uv run pytest
uv run ruff check .
uv run basedpyright
```

Consumers needing HTTP access should use [`unique-search-proxy-sdk`](../unique_search_proxy_sdk/README.md) rather than calling the proxy with raw httpx.

---

## License

Proprietary — Unique AG
