# Unique Search Proxy

A unified web search proxy API that provides a consistent interface for multiple search backends. Built with Flask and designed for seamless integration with AI applications.

## Overview

This service acts as an abstraction layer over different search providers, allowing clients to switch between search engines without changing their integration code. Currently supports:

| Engine | Description |
|--------|-------------|
| **Google Custom Search** | Direct integration with Google's Custom Search JSON API |
| **Vertex AI (Gemini)** | AI-powered search using Google's Gemini models with grounding capabilities |

## Quick Start

### Prerequisites

- Python 3.12+
- Poetry for dependency management
- Google Cloud credentials (for Vertex AI)
- Google Custom Search API key and Engine ID (for Google Search)

### Installation

```bash
# Install dependencies
poetry install

# Copy and configure environment variables
cp .env.example .env
```

### Environment Variables

```bash
# Google Custom Search
GOOGLE_SEARCH_API_KEY=your-api-key
GOOGLE_SEARCH_API_ENDPOINT=https://www.googleapis.com/customsearch/v1
GOOGLE_SEARCH_ENGINE_ID=your-engine-id

# Vertex AI
VERTEXAI_SERVICE_ACCOUNT_CREDENTIALS=path/to/credentials.json
```

### Running the Service

**Development:**
```bash
poetry run python app.py
```

**Production:**
```bash
./entrypoint.sh
```

Or with custom configuration:
```bash
HOST=0.0.0.0 PORT=8080 WORKERS=4 ./entrypoint.sh
```

**Docker:**
```bash
# Build the image
docker build -t search-proxy .

# Run the container (map port 8080 to host)
docker run --rm -p 8080:8080 search-proxy

# With custom environment variables
docker run --rm -p 8080:8080 -e WORKERS=8 -e LOG_LEVEL=debug search-proxy
```

## API Reference

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy"
}
```

---

### Search

```http
POST /search
Content-Type: application/json
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `search_engine` | string | No | `"google"` or `"vertexai"` (default: `"google"`) |
| `query` | string | Yes | The search query |
| `kwargs` | object | No | Engine-specific parameters |

**Response:**
```json
{
  "results": [
    {
      "url": "https://example.com/article",
      "title": "Article Title",
      "snippet": "A brief description of the content...",
      "content": ""
    }
  ]
}
```

---

## Search Engine Configuration

### Google Custom Search

Uses Google's Custom Search JSON API for traditional web search results.

**Parameters (`kwargs`):**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cx` | string | env default | Custom Search Engine ID (overrides env) |
| `fetchSize` | int | 10 | Number of results to fetch |
| `timeout` | int | 10 | Request timeout in seconds |

**Example:**
```json
{
  "search_engine": "google",
  "query": "latest AI developments",
  "kwargs": {
    "fetchSize": 20,
    "timeout": 15
  }
}
```

---

### Vertex AI (Gemini)

Leverages Google's Gemini models with web grounding for AI-enhanced search results. This engine:

1. Uses Gemini to search and synthesize information from the web
2. Generates structured results with citations
3. Optionally resolves shortened/redirect URLs to final destinations

**Parameters (`kwargs`):**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `modelName` | string | `"gemini-2.5-flash"` | Gemini model to use |
| `entrepriseSearch` | bool | `false` | Use Enterprise Web Search |
| `systemInstruction` | string | (built-in) | Custom system prompt |
| `resolveUrls` | bool | `true` | Resolve redirect URLs |

**Example:**
```json
{
  "search_engine": "vertexai",
  "query": "Compare the top 3 cloud providers for ML workloads",
  "kwargs": {
    "modelName": "gemini-2.5-flash",
    "resolveUrls": true
  }
}
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Flask App                            │
│                      /search endpoint                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                    ┌─────▼─────┐
                    │  Factory  │
                    └─────┬─────┘
                          │
          ┌───────────────┼───────────────┐
          │                               │
    ┌─────▼─────┐                   ┌─────▼─────┐
    │  Google   │                   │ Vertex AI │
    │  Search   │                   │  (Gemini) │
    └───────────┘                   └───────────┘
```

The service uses a **factory pattern** to register and resolve search engines, making it easy to add new backends.

## Error Handling

All errors return a consistent format:

```json
{
  "status": "failed",
  "error": "Error description"
}
```

| Status Code | Description |
|-------------|-------------|
| 400 | Validation error (invalid request) |
| 500 | Internal server error |

## Production Deployment

The service includes a production-ready `entrypoint.sh` that uses Gunicorn:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8080` | Listen port |
| `WORKERS` | `4` | Gunicorn workers |
| `TIMEOUT` | `120` | Request timeout |
| `LOG_LEVEL` | `info` | Logging verbosity |

## Development

```bash
# Run with hot reload
poetry run python app.py

# Format code
poetry run ruff format .

# Lint
poetry run ruff check .
```

## License

Proprietary - Unique AG

