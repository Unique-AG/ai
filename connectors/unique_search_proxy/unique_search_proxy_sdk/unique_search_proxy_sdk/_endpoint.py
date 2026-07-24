"""Async endpoint factories with ParamSpec signatures from core request models."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, ParamSpec, Protocol, TypeVar, cast

import httpx
from pydantic import BaseModel

from unique_search_proxy_sdk._http import unwrap_response
from unique_search_proxy_sdk._transport import OpenapiTransport
from unique_search_proxy_sdk.errors import raise_for_proxy_response

ResponseType = TypeVar("ResponseType")
RequestConstructorSpec = ParamSpec("RequestConstructorSpec")


def _kwargs_without_none(**kwargs: Any) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value is not None}


class SdkBody(Protocol):
    def to_dict(self) -> dict[str, Any]: ...


def async_post_endpoint(
    transport: OpenapiTransport,
    request_model: Callable[RequestConstructorSpec, BaseModel],
    *,
    parse: Callable[[object], BaseModel],
    to_sdk: Callable[[BaseModel], SdkBody],
    post: Callable[..., Awaitable[Any]],
    response_type: type[ResponseType],
) -> Callable[RequestConstructorSpec, Awaitable[ResponseType]]:
    """Build an async POST caller whose kwargs match ``request_model``."""
    _ = response_type

    async def call(
        *args: RequestConstructorSpec.args,
        **kwargs: RequestConstructorSpec.kwargs,
    ) -> ResponseType:
        constructed = request_model(*args, **_kwargs_without_none(**kwargs))
        validated = parse(
            constructed.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        sdk_body = to_sdk(validated)
        response = await post(
            client=transport.openapi,
            body=sdk_body,
            **transport.context_header_kwargs(),
        )
        return cast(ResponseType, unwrap_response(response))

    return call


def async_sse_endpoint(
    transport: OpenapiTransport,
    path: str,
    request_model: Callable[RequestConstructorSpec, BaseModel],
    *,
    parse: Callable[[object], BaseModel],
    to_sdk: Callable[[BaseModel], SdkBody],
) -> Callable[RequestConstructorSpec, AsyncIterator[dict[str, Any]]]:
    """Build an async SSE stream caller whose kwargs match ``request_model``."""

    async def stream(
        *args: RequestConstructorSpec.args,
        **kwargs: RequestConstructorSpec.kwargs,
    ) -> AsyncIterator[dict[str, Any]]:
        constructed = request_model(*args, **_kwargs_without_none(**kwargs))
        validated = parse(
            constructed.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        sdk_body = to_sdk(validated)
        http_client = transport.openapi.get_async_httpx_client()
        base_url = transport.base_url
        async with http_client.stream(
            "POST",
            f"{base_url}{path}",
            json=sdk_body.to_dict(),
            headers={"Content-Type": "application/json"},
        ) as response:
            if response.status_code >= 400:
                raw = await response.aread()
                raise_for_proxy_response(
                    httpx.Response(
                        status_code=response.status_code,
                        content=raw,
                        headers=dict(response.headers),
                    ),
                )
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                yield json.loads(line.removeprefix("data: "))

    return stream


__all__ = ["async_post_endpoint", "async_sse_endpoint"]
