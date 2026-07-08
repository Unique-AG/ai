from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from unique_search_proxy_core.param_policy.resolver import ConfigRequestResolver
from unique_search_proxy_core.search_engines.brave.schema import BraveConfig

from unique_search_proxy_client.web.core.search_engines.pagination import PageRequest


def build_brave_query_params(
    *,
    query: str,
    request: BaseModel,
    page: PageRequest,
) -> dict[str, Any]:
    """Assemble the Brave Web Search API query string from the derived request."""
    return {
        "q": query,
        "count": page.count,
        "offset": page.offset,
        **ConfigRequestResolver.provider_query_params(
            request, BraveConfig, by_alias=False
        ),
    }


__all__ = ["build_brave_query_params"]
