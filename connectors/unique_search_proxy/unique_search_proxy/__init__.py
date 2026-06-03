"""unique-search-proxy — one installable package, two layers.

**Application** — ``unique_search_proxy.web``

    FastAPI service, provider registry, ``HttpClientPool`` (egress to Google and
    the public web). Deploy as the proxy pod; entrypoint:
    ``uvicorn unique_search_proxy.web.app:app``.

**SDK** — ``unique_search_proxy.sdk``

    Hand-maintained async HTTP client for the service OpenAPI contract. Use from
    callers (e.g. ``unique_web_search``) over ``http://unique-search-proxy:2349``.
    Does not import or reuse the application egress pool.

Prefer explicit SDK imports::

    from unique_search_proxy.sdk import UniqueSearchProxyClient

Root re-exports are convenience aliases only.
"""

from unique_search_proxy.sdk import (
    UniqueSearchProxyClient,
    UniqueSearchProxyClientError,
)

__all__ = ["UniqueSearchProxyClient", "UniqueSearchProxyClientError"]
