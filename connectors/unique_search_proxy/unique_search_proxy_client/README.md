# Unique Search Proxy

Unified web egress proxy for search engines and crawlers. **Three publishable packages** in this repo:

| PyPI name | Module | Role |
|-----------|--------|------|
| `unique-search-proxy` | `unique_search_proxy_client.web` | FastAPI server (proxy pod) |
| `unique-search-proxy-sdk` | `unique_search_proxy_sdk` | Async HTTP client for callers |
| `unique-search-proxy-core` | `unique_search_proxy_core` | Shared Pydantic types (no FastAPI) |

```mermaid
flowchart LR
  subgraph caller["Caller pod"]
    SDK["unique_search_proxy_sdk"]
  end
  subgraph proxy["Proxy pod"]
    API["unique_search_proxy_client.web"]
    Pool["HttpClientPool"]
  end
  Core["unique_search_proxy_core"]
  Internet["Google / public web"]
  SDK --> Core
  API --> Core
  SDK -->|"POST /v1/search"| API
  API --> Pool
  Pool --> Internet
```

- **Server** owns registry, secrets, Prometheus, and egress (`HttpClientPool`).
- **SDK** wraps the [OpenAPI](http://localhost:2349/docs) contract; depends on **core** for `GoogleConfig`, errors, etc.
- **Core** is server-free and safe to install without FastAPI/uvicorn.

## Quick Start

### Prerequisites

- Python 3.12+
- uv for dependency management

### Installation

```bash
uv sync
cp .env.example .env
# Edit .env: set GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID for live /v1/search
```

### Running

```bash
uv run python -m unique_search_proxy_client.web.app
# or
uv run uvicorn unique_search_proxy_client.web.app:app --reload --port 2349
```

## Python SDK (`unique-search-proxy-sdk`)

Workspace path: `connectors/unique_search_proxy/unique_search_proxy_sdk/`. Generated from the server OpenAPI spec via [openapi-python-client](https://github.com/openapi-generators/openapi-python-client).

| Path | Role |
|------|------|
| `unique_search_proxy_sdk/_generated/` | Regenerated httpx client + attrs models |
| `unique_search_proxy_sdk/client.py` | `UniqueSearchProxyClient` facade |
| `connectors/unique_search_proxy/unique_search_proxy_client/openapi.json` | Exported spec (codegen input) |

### Regenerate after API changes

```bash
cd connectors/unique_search_proxy/unique_search_proxy_client
uv sync
uv run python scripts/generate_sdk.py
```

### Usage

```python
from unique_search_proxy_sdk import UniqueSearchProxyClient

async with UniqueSearchProxyClient("http://unique-search-proxy:2349") as client:
    await client.health()
    result = await client.search.search("unique ag", engine="google", fetchSize=10)
    agent = await client.agent_search.search(
        "EU AI Act timeline",
        engine="bing",
        generationInstructions="...",
    )
    crawl = await client.crawl.crawl(["https://example.com"], crawler="basic")

    # Low-level: one generated function per route
    raw = client.openapi  # OpenAPIClient from _generated
```

| Facade method | HTTP |
|---------------|------|
| `health()` | `GET /health` |
| `ready()` | `GET /ready` |
| `search.search(...)` | `POST /v1/search` |
| `agent_search.search(...)` | `POST /v1/agent-search` |
| `agent_search.stream(...)` | `POST /v1/agent-search/stream` (SSE) |
| `crawl.crawl(...)` | `POST /v1/crawl` |

Deployment config JSON Schema, defaults, and LLM call-schema projection live in **`unique_search_proxy_core`** (not HTTP). Assistants-core and tooling import those helpers directly.

Non-success responses raise the same `ProxyError` subclasses as the service. Generated request/response models live under `sdk._generated.models`.

For tests, pass an `httpx.AsyncClient` with `ASGITransport(app=create_app())` and run the app lifespan so in-app egress is initialized.

### Other OpenAPI codegen tools

| Tool | Notes |
|------|--------|
| [OpenAPI Generator](https://github.com/OpenAPITools/openapi-generator) | Broad language support; verbose Python output |
| [openapi-python-client](https://github.com/openapi-generators/openapi-python-client) | **Used here** — async httpx + attrs |
| [datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator) | Pydantic models only |
| [Kiota](https://github.com/microsoft/kiota) | Multi-language SDKs |

## API (application)

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Liveness |
| `GET /ready` | Readiness (httpx pool + registered providers) |
| `GET /v1/configuration/providers` | Registered search engine, agent engine, and crawler ids |
| `POST /v1/search` | Execute search (flat request: `engine`, `query`, provider params, `timeout`) |
| `POST /v1/agent-search` | Agent-based grounded search — returns opaque `answer` + `raw` (Bing / VertexAI) |
| `POST /v1/agent-search/stream` | Same as above, streamed as SSE (`delta` + `done` events) |
| `POST /v1/crawl` | Crawl URLs via configured crawler (flat request: `crawler`, `urls`, `timeout`, …) |
| `GET /metrics` | Prometheus scrape endpoint (when enabled) |
| `/docs` | OpenAPI (Swagger UI) — use **Try it out** and the request-body **Examples** dropdown on `/v1/search` and `/v1/crawl` |

Set `ENABLED=false` on monitoring settings (`PrometheusSettings`) to disable metrics. With `WORKERS > 1`, the entrypoint sets `PROMETHEUS_MULTIPROC_DIR` for correct aggregation across uvicorn workers.

Settings are colocated with each component and use env prefixes:

| Component | Prefix / vars | Example |
|-----------|----------------|---------|
| Google search | (no prefix) | `GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_ENGINE_ID` |
| Brave search | (no prefix) | `BRAVE_SEARCH_API_KEY`, `BRAVE_SEARCH_API_ENDPOINT` |
| Perplexity search | (no prefix) | `PERPLEXITY_SEARCH_API_KEY`, `PERPLEXITY_SEARCH_API_ENDPOINT` |
| Tavily | `TAVILY_` | `TAVILY_API_KEY`, `TAVILY_API_ENDPOINT` |
| Jina | `JINA_` | `JINA_API_KEY`, `JINA_DEPLOYMENT` (`global` or `eu-beta`) |
| Firecrawl | `FIRECRAWL_` | `FIRECRAWL_API_KEY`, `FIRECRAWL_API_ENDPOINT`, `FIRECRAWL_API_VERSION` |
| Bing agent search | `BING_AGENT_` | `BING_AGENT_ENDPOINT`, `BING_AGENT_BING_RESOURCE_CONNECTION_STRING`, optional `BING_AGENT_AGENT_ID` |
| VertexAI agent search | `VERTEXAI_AGENT_` | Optional `VERTEXAI_AGENT_SERVICE_ACCOUNT_CREDENTIALS` (base64 JSON); ADC otherwise |

Unset secrets default to the sentinel `NOT_PROVIDED`. Search or crawl calls against an unconfigured provider return **503** `ENGINE_NOT_CONFIGURED` with the missing env var names in the error message (for operators and LLM tool consumers).
| HTTP client | `HTTP_CLIENT_` | `HTTP_CLIENT_PROXY_HOST`, `HTTP_CLIENT_POOL_TIMEOUT_SECONDS` |
| Prometheus | `PROMETHEUS_` | `PROMETHEUS_ENABLED` |
| Container entrypoint | (shell) | `HOST`, `PORT`, `WORKERS`, `LOG_LEVEL`, `PROMETHEUS_MULTIPROC_DIR` |

Copy `.env.example` to `.env` for an annotated template of all settings. Outbound HTTP/proxy pool settings live in `web/settings/client.py`; provider credentials in `web/settings/providers/`; shared helpers in `web/settings/base.py`.

### Runtime discovery (`GET /v1/configuration/providers`)

Lists search engine and crawler ids registered in the proxy pod (depends on env/secrets). Use this for health checks and capability discovery at runtime.

Deployment config JSON Schema and defaults are **core library** concerns — import from `unique_search_proxy_core.providers.schema`. Search LLM call-schema projection lives in `unique_search_proxy_core.search_engines.call_schema`. Crawlers use flat `POST /v1/crawl` bodies only (no per-crawler call-schema). Assistants-core embeds those shapes in tool manifests rather than calling extra HTTP routes on the proxy.

### Search (`POST /v1/search`)

Flat request body: all execution fields at the top level (`engine`, `query`, optional provider knobs, `timeout`). Tooling merges deployment config with LLM invocation in **core** (`merge_config_and_invocation`) before calling the proxy.

```json
{
  "engine": "google",
  "query": "example query",
  "fetchSize": 10,
  "gl": "de",
  "dateRestrict": "d7",
  "timeout": 30
}
```

- **`engine`**: registered search engine id (discriminator)
- **`query`**, **`fetchSize`**, optional provider knobs, **`timeout`**: flat execution payload on `POST /v1/search`
- **Deployment config** (`ExposableParam` with `expose` + `value`): resolved in core before building the flat search request — not a separate HTTP surface on the proxy
- **LLM call schema**: `unique_search_proxy_core.search_engines.call_schema.resolve_search_call_schema(...)` with optional `strict=False` for nullable exposed fields

Response:

```json
{
  "engine": "google",
  "query": "example query",
  "raw": {
    "pages": [
      {
        "pageIndex": 1,
        "offset": 1,
        "requestedCount": 10,
        "response": {}
      }
    ]
  },
  "curated": [
    {
      "url": "https://example.com",
      "title": "Example",
      "snippet": "...",
      "content": ""
    }
  ]
}
```

### Agent search (`POST /v1/agent-search`)

Thin egress for grounding agents (Bing via Azure AI Projects, VertexAI via Google GenAI). The proxy returns **opaque agent text** — consumers own parsing, citation extraction, and `WebSearchResult` mapping.

```json
{
  "engine": "bing",
  "query": "latest EU AI Act timeline",
  "generationInstructions": "... consumer composes full instructions ...",
  "fetchSize": 5,
  "timeout": 120
}
```

Response:

```json
{
  "engine": "bing",
  "query": "latest EU AI Act timeline",
  "answer": "raw assistant text from the provider",
  "raw": {}
}
```

Streaming (`POST /v1/agent-search/stream`) emits SSE `data:` lines with `{ "type": "delta", "text": "..." }` chunks and a terminal `{ "type": "done", "response": { ... } }`.

### Crawl (`POST /v1/crawl`)

```json
{
  "urls": ["https://example.com"],
  "crawler": "Basic",
  "timeout": 30
}
```

Registered crawler discriminators: `Basic`, `Tavily`, `Jina`, `Firecrawl`. Provider-specific fields (e.g. `extractDepth` for Tavily) are flat on the request body.

### Errors

Non-2xx responses use a structured envelope:

```json
{
  "error": {
    "code": "ENGINE_NOT_CONFIGURED",
    "message": "Engine 'google' is not registered or not configured",
    "engine": "google",
    "retryable": false
  }
}
```

## Project Structure

```
connectors/unique_search_proxy/
├── unique_search_proxy/
│   ├── sdk/                    # HTTP SDK (callers → proxy API)
│   │   ├── _generated/         # openapi-python-client output (regenerate via scripts/)
│   │   ├── client.py           # UniqueSearchProxyClient facade
│   │   ├── converters.py       # App Pydantic config → generated models
│   │   └── errors.py           # Maps API error envelope → ProxyError
│   ├── openapi.json            # Exported OpenAPI (codegen input)
│   ├── scripts/generate_sdk.py
│   └── web/                    # FastAPI application (proxy pod)
│       ├── app.py              # App factory + lifespan (HttpClientPool)
│       ├── settings/
│       ├── api/
│       │   ├── health.py
│       │   └── v1/
│       │       ├── configuration.py
│       │       ├── search.py
│       │       └── crawl.py
│       ├── monitoring/
│       └── core/
│           ├── client/         # Egress pool — application only, not SDK
│           ├── search_engines/
│           └── crawlers/
├── tests/
└── deploy/
```

Engines and crawlers register via `web/core/registry.py` at application startup.

## Dev testing (payloads and responses)

Verify config payloads by sending curated presets to a running local proxy and inspecting request/response JSON.

1. Start the server and configure `.env` (see [Quick Start](#quick-start)).
2. **Swagger** — open `/docs`, use **Try it out** on `POST /v1/search` or `POST /v1/crawl`, pick a preset from the **Examples** dropdown, execute, and read the response.
3. **CLI** — same presets from the terminal:

```bash
# List presets
uv run python scripts/try_presets.py list

# Run one preset (prints request + response JSON)
uv run python scripts/try_presets.py run tavily_rerank

# Run all crawl presets
uv run python scripts/try_presets.py run-all --kind crawl

# Against a port-forwarded cluster pod
uv run python scripts/try_presets.py run google_minimal --base-url http://127.0.0.1:8080
```

Presets live in `unique_search_proxy_client/web/presets/` (single source of truth for Swagger examples and the CLI). Unconfigured providers return **503** `ENGINE_NOT_CONFIGURED` with `missingEnvVars` in the error body — same as production calls.

Add `--strict` to exit non-zero when any response is not 2xx.

## Development

```bash
uv run ruff check .
uv run ruff format .
uv run pytest
uv run basedpyright
```

## License

Proprietary - Unique AG
