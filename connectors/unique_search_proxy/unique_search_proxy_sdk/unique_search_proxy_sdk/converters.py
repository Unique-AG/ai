"""Convert core Pydantic request models to OpenAPI-generated SDK models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


@dataclass(frozen=True, slots=True)
class SdkSearchBody:
    """JSON body for ``POST /v1/search`` without attrs ``from_dict``.

    The generated attrs request models are fragile under IPython ``%autoreload``
    (attrs-generated ``__init__`` can raise read-only attribute errors after a
    reload). The OpenAPI route only needs ``to_dict()`` for serialization, so we
    pass validated core payloads through this wrapper instead.
    """

    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return self.payload


@dataclass(frozen=True, slots=True)
class SdkCrawlBody:
    """JSON body for ``POST /v1/crawl`` without attrs ``from_dict``."""

    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return self.payload


@dataclass(frozen=True, slots=True)
class SdkAgentSearchBody:
    """JSON body for ``POST /v1/agent-search`` without attrs ``from_dict``."""

    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return self.payload


def _model_to_sdk_dict(model: BaseModel) -> dict[str, Any]:
    """Serialize a resolver-built request model to a flat JSON body.

    Derived request models no longer carry ``ExposableParam`` instances, so a plain
    ``model_dump`` produces the flat provider payload the API expects.
    """
    return model.model_dump(mode="json", by_alias=True, exclude_none=True)


def to_sdk_search_request(request: BaseModel) -> SdkSearchBody:
    """Build the HTTP JSON body for a validated core search request."""
    return SdkSearchBody(payload=_model_to_sdk_dict(request))


def to_sdk_crawl_request(request: BaseModel) -> SdkCrawlBody:
    """Build the HTTP JSON body for a validated core crawl request."""
    return SdkCrawlBody(payload=_model_to_sdk_dict(request))


def to_sdk_agent_search_request(request: BaseModel) -> SdkAgentSearchBody:
    """Build the HTTP JSON body for a validated core agent-search request."""
    return SdkAgentSearchBody(payload=_model_to_sdk_dict(request))
