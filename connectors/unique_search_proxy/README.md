# Unique Search Proxy

Unified web egress proxy for search engines and crawlers. Built with FastAPI; providers are registered at runtime and invoked via a versioned HTTP API.

## Quick Start

### Prerequisites

- Python 3.12+
- uv for dependency management

### Installation

```bash
uv sync
cp .env.example .env  # when present
```

### Running

```bash
uv run python -m unique_search_proxy.web.app
# or
uv run uvicorn unique_search_proxy.web.app:app --reload --port 2349
```

## API

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Liveness |
| `GET /ready` | Readiness (httpx pool + registered providers) |
| `POST /v1/search` | Search via configured engine |
| `POST /v1/crawl` | Crawl URLs via configured crawler |
| `GET /metrics` | Prometheus scrape endpoint (when enabled) |
| `/docs` | OpenAPI (Swagger UI) |

Set `ENABLED=false` on monitoring settings (`PrometheusSettings`) to disable metrics. With `WORKERS > 1`, the entrypoint sets `PROMETHEUS_MULTIPROC_DIR` for correct aggregation across uvicorn workers.

Settings are colocated with each component and use env prefixes:

| Component | Prefix | Example |
|-----------|--------|---------|
| HTTP client | `HTTP_CLIENT_` | `HTTP_CLIENT_PROXY_HOST`, `HTTP_CLIENT_POOL_TIMEOUT_SECONDS` |
| URL safety | `URL_SAFETY_` | `URL_SAFETY_ENABLED` |
| Prometheus | `PROMETHEUS_` | `PROMETHEUS_ENABLED` |

Shared helpers live in `web/settings/`.

### Search (`POST /v1/search`)

```json
{
  "query": "example query",
  "config": { "engine": "google" },
  "includeContent": false,
  "timeout": 30
}
```

Response:

```json
{
  "engine": "google",
  "query": "example query",
  "raw": {},
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

### Crawl (`POST /v1/crawl`)

```json
{
  "urls": ["https://example.com"],
  "config": { "crawler": "basic" },
  "parallel": true,
  "timeout": 30
}
```

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
│   └── web/
│       ├── app.py              # FastAPI app factory
│       ├── settings/           # Shared settings helpers (env path, config factory)
│       ├── api/
│       │   ├── health.py       # /health, /ready
│       │   └── v1/             # Versioned API
│       │       ├── schema.py   # Request/response models
│       │       ├── search.py
│       │       └── crawl.py
│       ├── monitoring/         # Prometheus metrics (unique_toolkit)
│       └── core/
│           ├── schema.py       # Shared domain types
│           ├── errors.py
│           ├── registry.py
│           ├── client/         # HTTP egress service (settings + pool)
│           ├── search_engines/
│           └── crawlers/
│               └── url_safety/
├── tests/
└── deploy/
```

Engines and crawlers are registered via `core/registry.py` (empty until provider milestones land).

## Development

```bash
uv run ruff check .
uv run ruff format .
uv run pytest
uv run basedpyright
```

## License

Proprietary - Unique AG
