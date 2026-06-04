# unique-search-proxy-sdk

Async HTTP client for the [Unique Search Proxy](https://github.com/unique-ag/ai) service.

```python
from unique_search_proxy_sdk import UniqueSearchProxyClient

async with UniqueSearchProxyClient("http://unique-search-proxy:2349") as client:
    health = await client.health()
```

Depends on `unique-search-proxy-core` for typed configuration models. Does not include the FastAPI server.
