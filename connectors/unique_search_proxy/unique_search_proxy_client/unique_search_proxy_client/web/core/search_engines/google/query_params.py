from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from unique_search_proxy_core.param_policy.resolver import ConfigRequestResolver
from unique_search_proxy_core.search_engines.google.schema import GoogleConfig

from unique_search_proxy_client.web.core.search_engines.pagination import PageRequest


def build_google_query_params(
    *,
    query: str,
    api_key: str,
    search_engine_id: str,
    request: BaseModel,
    page: PageRequest,
) -> dict[str, Any]:
    """Assemble the Google API query string from the derived request + credentials."""
    return {
        "q": query,
        "cx": search_engine_id,
        "key": api_key,
        "start": page.offset,
        "num": page.count,
        **ConfigRequestResolver.provider_query_params(request, GoogleConfig),
    }


__all__ = ["build_google_query_params"]
