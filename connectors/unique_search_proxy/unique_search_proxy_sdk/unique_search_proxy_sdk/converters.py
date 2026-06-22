"""Convert core Pydantic request models to OpenAPI-generated SDK models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from unique_search_proxy_core.param_policy.exposable_param import ExposableParam


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
    data = model.model_dump(mode="json", by_alias=True, exclude_none=True)
    for name, field in type(model).model_fields.items():
        raw = getattr(model, name)
        if isinstance(raw, ExposableParam):
            key = field.serialization_alias or field.alias or name
            data[key] = raw.model_dump(mode="json", by_alias=True)
    return data


def to_sdk_search_request(request: BaseModel) -> SdkSearchBody:
    """Build the HTTP JSON body for a validated core search request."""
    return SdkSearchBody(payload=_model_to_sdk_dict(request))


def to_sdk_crawl_request(request: BaseModel) -> SdkCrawlBody:
    """Build the HTTP JSON body for a validated core crawl request."""
    return SdkCrawlBody(payload=_model_to_sdk_dict(request))


def to_sdk_agent_search_request(request: BaseModel) -> SdkAgentSearchBody:
    """Build the HTTP JSON body for a validated core agent-search request."""
    return SdkAgentSearchBody(payload=_model_to_sdk_dict(request))
