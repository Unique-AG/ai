# Search Engines

Implementations wrap standard search APIs and grounding (agent) providers behind a common `SearchEngine` interface. Runtime dispatch prefers **Unique Search Proxy** when enabled.

## Proxy vs legacy

```python
# SearchEngine.search (services/search_engine/base.py)
if search_proxy_client_enabled and engine is proxy-supported:
    return await self._proxy_search(...)   # standard → /v1/search; agent → /v1/agent-search
return await self._legacy_search(...)      # direct provider call from this process
```

| Kind | Engines | Proxy | Legacy |
|------|---------|-------|--------|
| **Standard** | Google | yes | yes |
| **Standard** | Brave, Perplexity | yes | **raises** (proxy-only) |
| **Standard** | Custom API | never | always |
| **Agent** | Bing, VertexAI | yes | yes |

Deployment configs for Google / Brave / Perplexity (and agent base fields) live in **`unique_search_proxy_core`**. This package registers tool wrappers and adds web-only fields where needed (e.g. `requires_scraping` on Bing/VertexAI).

---

## Standard vs agent

| | Standard | Agent (grounding) |
|--|----------|-------------------|
| Proxy route | `POST /v1/search` | `POST /v1/agent-search` |
| Result shape | `SearchResponse` → `WebSearchResult` list | Opaque `answer` text → parsed locally |
| LLM knobs | `ExposableParam` + `config.merge()` | No exposable params |
| Typical scrape | Often yes (Google) | Often no (`requires_scraping=false`) |

---

## Exposable parameters (standard search only)

Optional provider knobs use `ExposableParam[T]` from `unique_search_proxy_core.param_policy.exposable_param`:

```python
ExposableParam(expose=False, value="us")  # fixed admin default; omitted from LLM schema
ExposableParam(expose=True, value="us")   # default + visible on exposed_params_model()
ExposableParam(expose=False, value=None)  # deactivated (not merged into the request)
```

| `expose` | `value` | Behaviour |
|----------|---------|-----------|
| any | `None` | Knob off — not sent to the provider |
| `False` | set | Merged as fixed default; **not** on the LLM tool schema |
| `True` | set / `None` | Included on `exposed_params_model()`; merge uses `value` when not `None` |

**Derive helpers on config:**

- `config.exposed_params_model()` — LLM-facing subset
- `config.merge(llm_overrides, query=...)` — flat HTTP body for the proxy (no nested config+invocation)

Crawlers and agent engines do **not** use this pattern.

```python
from unique_search_proxy_core.param_policy.exposable_param import ExposableParam
from unique_search_proxy_core.search_engines.google.schema import GoogleConfig

config = GoogleConfig(
    fetch_size=10,
    safe="active",
    gl=ExposableParam(expose=False, value="ch"),  # locked country
    date_restrict=ExposableParam(expose=True, value=None),  # AI may set per call
)
body = config.merge({"dateRestrict": "m1"}, query="EU AI Act")
```

---

## Standard engines

### Google Search

**Provider:** Google Custom Search JSON API · **Requires scraping:** yes · **Proxy:** legacy + proxy

Config: `unique_search_proxy_core.search_engines.google.schema.GoogleConfig`

| Field | Notes |
|-------|-------|
| `fetch_size` | Result count |
| `search_engine_id` | CSE `cx` (credential; not a query knob) |
| `safe` | `active` / `off` (not exposable) |
| `gl`, `hl`, `lr`, `date_restrict`, `exact_terms`, `exclude_terms`, `file_type`, `site_search`, `site_search_filter`, `sort` | `ExposableParam` |

```bash
GOOGLE_SEARCH_API_KEY=...
GOOGLE_SEARCH_ENGINE_ID=...
```

### Brave Search (proxy-only)

**Provider:** Brave Search API · **Requires scraping:** typically no (rich snippets) · **Legacy:** not supported

Config: `unique_search_proxy_core.search_engines.brave.schema.BraveConfig`

Fixed bools include `extra_snippets`, `spellcheck`, `text_decorations`. Exposable knobs include country, search language, result filter, and related locale fields (see schema for full list).

```bash
BRAVE_SEARCH_API_KEY=...
```

```python
from unique_search_proxy_core.search_engines.brave.schema import BraveConfig
from unique_web_search.services.search_engine.brave import BraveSearch

search = BraveSearch(BraveConfig(fetch_size=10))
results = await search.search("privacy-focused search")  # requires SEARCH_PROXY_BASE_URL
```

### Perplexity Search (proxy-only)

**Provider:** Perplexity Search API · **Legacy:** not supported

Config: `unique_search_proxy_core.search_engines.perplexity.schema.PerplexityConfig`

| Field | Notes |
|-------|-------|
| `search_context_size` | `low` / `medium` / `high` |
| `max_tokens`, `max_tokens_per_page` | Optional token caps |
| `country`, `search_language_filter`, `search_domain_filter`, `search_recency_filter`, date filters | `ExposableParam` |

```bash
PERPLEXITY_API_KEY=...
```

### Custom API Search (always local)

**Provider:** your REST endpoint · **Never proxy-routed**

Config: `unique_web_search.services.search_engine.custom_api.CustomAPIConfig` (`LocalSearchEngineType.CUSTOM_API`)

Response must be JSON with a `results` array of `{url, title, snippet, content?}`.

```bash
CUSTOM_WEB_SEARCH_API_ENDPOINT=https://your-api.example.com/search
CUSTOM_WEB_SEARCH_API_METHOD=POST
CUSTOM_WEB_SEARCH_API_HEADERS='{"Authorization": "Bearer ..."}'
```

---

## Agent engines (grounding)

### Bing (Grounding with Bing)

**Provider:** Azure AI Foundry Agent with Bing grounding · Config extends `BingAgentConfig` with `requires_scraping`, `language_model`, etc.

```bash
AZURE_AI_PROJECT_ENDPOINT=...
AZURE_AI_AGENT_ID=...          # optional; empty → auto-provision
AZURE_IDENTITY_CREDENTIAL_TYPE=workload  # or default
```

### VertexAI (Grounding with VertexAI)

**Provider:** Gemini + Google Search grounding on Vertex AI · Config extends `VertexAIAgentConfig`.

Requires GCP ADC / workload identity. Fields include `vertexai_model_name`, `generation_instructions`, `enable_entreprise_search`, `enable_redirect_resolution`, `requires_scraping`.

---

## Factory

```python
from unique_web_search.services.search_engine import get_search_engine_service

engine = get_search_engine_service(config, language_model_service, lmi)
results = await engine.search("query")
```

Modules register with `@register_search_engine(...)` and are auto-discovered. Keep static unions in `__init__.py` in sync (see `tests/test_search_engine_registry.py`).

## Adding an engine

1. Prefer defining config in `unique_search_proxy_core` for proxy-routed engines.
2. Add a tool module with `@register_search_engine`; implement `_legacy_search` (or raise if proxy-only).
3. Extend static `SearchEngineConfigTypes` / `SearchEngineTypes` unions.
4. Add tests in `tests/test_search_engines.py` / registry tests.

## Result schema

```python
class WebSearchResult(BaseModel):
    url: str
    title: str
    snippet: str
    content: str
```
