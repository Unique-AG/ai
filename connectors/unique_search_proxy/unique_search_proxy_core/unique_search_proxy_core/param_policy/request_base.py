"""Base models carrying the required leading field of every derived request.

Every request model derived from a deployment config subclasses one of these,
so the required ``query`` / ``urls`` field lives in exactly one place instead of
being re-declared per derivation. Consumed by ``param_policy.derive``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from unique_search_proxy_core.schema import (
    camelized_model_config,
    deployment_model_config,
)


class SearchRequestBase(BaseModel):
    """Base for derived ``POST /v1/search`` bodies: carries the required ``query``."""

    model_config = camelized_model_config
    query: str = Field(..., min_length=1, description="Search query string")


class AgentRequestBase(SearchRequestBase):
    """Base for derived ``POST /v1/agent-search`` bodies (same required ``query``)."""


class CrawlRequestBase(BaseModel):
    """Base for derived ``POST /v1/crawl`` bodies: carries the required ``urls``.

    Uses ``deployment_model_config`` (``extra='forbid'``) to match the crawler
    configs' schema (``additionalProperties: false``).
    """

    model_config = deployment_model_config
    urls: list[str] = Field(..., min_length=1, description="URLs to crawl")
