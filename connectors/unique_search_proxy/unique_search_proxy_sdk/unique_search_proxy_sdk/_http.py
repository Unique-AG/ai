"""Helpers for OpenAPI client responses."""

from __future__ import annotations

from typing import TypeVar, cast

import httpx

from unique_search_proxy_sdk._generated.types import Response
from unique_search_proxy_sdk.errors import (
    UniqueSearchProxyClientError,
    raise_for_proxy_response,
)

T = TypeVar("T")


def unwrap_response(response: Response[T]) -> T:
    """Return parsed body or raise proxy-typed errors from the raw HTTP response."""
    status_code = int(response.status_code)
    if status_code >= 400:
        raise_for_proxy_response(
            httpx.Response(
                status_code=status_code,
                content=response.content,
                headers=dict(response.headers),
            ),
        )
    if response.parsed is None:
        msg = f"Empty response body for HTTP {status_code}"
        raise UniqueSearchProxyClientError(msg)
    return cast(T, response.parsed)
