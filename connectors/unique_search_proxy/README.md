# Unique Search Proxy (connectors)

Monorepo layout for the web search / crawl egress proxy:

```
connectors/unique_search_proxy/
├── unique_search_proxy_client/   # FastAPI server, Docker, Helm (`unique-search-proxy`)
├── unique_search_proxy_core/     # Shared Pydantic types (`unique-search-proxy-core`)
└── unique_search_proxy_sdk/      # HTTP client (`unique-search-proxy-sdk`)
```

See each package's `README.md` for install and usage.
