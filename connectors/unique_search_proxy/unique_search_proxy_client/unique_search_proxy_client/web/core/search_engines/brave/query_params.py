from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from unique_search_proxy_core.search_engines.brave.schema import BraveConfig

from unique_search_proxy_client.web.core.search_engines.pagination import PageRequest


def build_brave_query_params(
    *,
    query: str,
    request: BaseModel,
    page: PageRequest,
) -> dict[str, Any]:
    """Assemble the Brave Web Search API query string from the derived request."""
    config = BraveConfig()
    return {
        "q": query,
        "count": page.count,
        "offset": page.offset,
        **config.provider_query_params_from(request, by_alias=False),
    }


__all__ = ["build_brave_query_params"]
