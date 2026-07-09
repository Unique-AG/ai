"""Base models that carry the required ``query`` for derived request/call models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from unique_search_proxy_core.schema import (
    camelized_model_config,
    deployment_model_config,
)


class SearchRequestBase(BaseModel):
    """Base for derived request/call models: carries the required ``query``."""

    model_config = camelized_model_config
    query: str = Field(..., min_length=1, description="Search query string")


class AgentRequestBase(SearchRequestBase):
    """Agent request base (same required ``query``)."""


class CrawlRequestBase(BaseModel):
    """Base for derived crawl request models: carries the required ``urls``.

    Uses ``deployment_model_config`` (``extra='forbid'``) to match the crawler
    config's schema (``additionalProperties: false``).
    """

    model_config = deployment_model_config
    urls: list[str] = Field(..., min_length=1, description="URLs to crawl")
