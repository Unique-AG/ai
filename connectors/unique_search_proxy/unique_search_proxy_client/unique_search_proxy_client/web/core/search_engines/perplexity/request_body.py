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
    params = PerplexityConfig.provider_query_params(request, by_alias=False)
    params = _apply_perplexity_api_rules(params)
    return {
        "query": query,
        "max_results": max_results,
        **params,
    }


def _apply_perplexity_api_rules(params: dict[str, Any]) -> dict[str, Any]:
    """Apply Perplexity API rules to the request parameters."""
    # Perplexity API rule: omit ``search_context_size`` when a token limit is set.
    if (
        params.get("max_tokens") is not None
        or params.get("max_tokens_per_page") is not None
    ):
        params.pop("search_context_size", None)
    return params


__all__ = ["PERPLEXITY_MAX_RESULTS", "build_perplexity_request_body"]
