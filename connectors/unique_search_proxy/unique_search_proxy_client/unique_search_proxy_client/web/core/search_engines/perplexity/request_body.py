from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel
from unique_search_proxy_core.search_engines.perplexity.schema import PerplexityConfig

PERPLEXITY_MAX_RESULTS = 20
"""Perplexity Search API allows at most 20 results per request."""

_LOGGER = logging.getLogger(__name__)


def build_perplexity_request_body(
    *,
    query: str,
    request: BaseModel,
) -> dict[str, Any]:
    """Assemble the Perplexity Search API JSON body from the derived request."""
    config = PerplexityConfig()
    fetch_size = getattr(request, "fetch_size", PERPLEXITY_MAX_RESULTS)
    max_results = min(fetch_size, PERPLEXITY_MAX_RESULTS)
    if fetch_size > PERPLEXITY_MAX_RESULTS:
        _LOGGER.warning(
            "Perplexity Search API allows at most %s results per request; "
            "capping max_results from %s to %s",
            PERPLEXITY_MAX_RESULTS,
            fetch_size,
            max_results,
        )
    return {
        "query": query,
        "max_results": max_results,
        **config.provider_query_params_from(request, by_alias=False),
    }


__all__ = ["PERPLEXITY_MAX_RESULTS", "build_perplexity_request_body"]
