"""Shared OpenAPI HTTP transport for SDK clients."""

from __future__ import annotations

from typing import Any

import httpx
from unique_search_proxy_core.context import LOCAL_REQUEST_CONTEXT, RequestContext
from unique_search_proxy_core.logging import suppress_httpx_request_logs

from unique_search_proxy_sdk._generated.api.health import (
    health_health_get,
    ready_ready_get,
)
from unique_search_proxy_sdk._generated.client import Client as OpenAPIClient
from unique_search_proxy_sdk._http import unwrap_response

_DEFAULT_TIMEOUT_SECONDS = 60.0


class OpenapiTransport:
    """Lifecycle wrapper around the generated ``openapi-python-client`` client."""

    def __init__(
        self,
        base_url: str,
        *,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = _DEFAULT_TIMEOUT_SECONDS,
        context: RequestContext = LOCAL_REQUEST_CONTEXT,
    ) -> None:
        suppress_httpx_request_logs()
        self._base_url = base_url.rstrip("/")
        self._owns_client = http_client is None
        self._context = context
        self._openapi = OpenAPIClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout),
            headers=context.to_headers(),
        )
        if http_client is not None:
            http_client.headers.update(context.to_headers())
            self._openapi.set_async_httpx_client(http_client)

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def openapi(self) -> OpenAPIClient:
        return self._openapi

    @property
    def context(self) -> RequestContext:
        return self._context

    def context_header_kwargs(self) -> dict[str, str]:
        """Per-request context kwargs for the generated ``/v1`` route helpers.

        The generated helpers default ``x_unique_company_id`` / ``x_unique_user_id``
        / ``x_unique_chat_id`` to ``"local"`` and always attach them as request
        headers. In httpx, request headers win over the client-level default
        headers, so relying on the client-level context alone silently resets a
        non-local context to ``"local"`` on every call. Forwarding these keeps the
        transport's context authoritative.
        """
        return {
            "x_unique_company_id": self._context.company_id,
            "x_unique_user_id": self._context.user_id,
            "x_unique_chat_id": self._context.chat_id,
        }

    async def aclose(self) -> None:
        if self._owns_client:
            await self._openapi.get_async_httpx_client().aclose()

    async def __aenter__(self) -> OpenapiTransport:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def health(self) -> dict[str, Any]:
        response = await health_health_get.asyncio_detailed(client=self._openapi)
        body = unwrap_response(response)
        return body.to_dict()

    async def ready(self) -> dict[str, Any]:
        response = await ready_ready_get.asyncio_detailed(client=self._openapi)
        body = unwrap_response(response)
        return body.to_dict()


__all__ = ["OpenapiTransport"]
