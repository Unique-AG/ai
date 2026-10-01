from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import urlsplit

import httpx
from pydantic import ValidationError
from unique_search_proxy_core.errors import (
    BadRequestProxyError,
    ForbiddenTargetError,
    UpstreamError,
    UpstreamTimeoutError,
)
from unique_search_proxy_core.schema import SearchEngineRaw, WebSearchResults
from unique_search_proxy_core.search_engines.base import (
    SearchEngineType,
    get_search_engine_mode,
)
from unique_search_proxy_core.search_engines.custom_api.schema import (
    CustomApiRequestMethod,
    CustomApiSearchRequest,
)
from unique_search_proxy_core.url_safety import (
    CrawlTargetValidationError,
    UrlSafetyService,
    pinned_httpx_get_args,
)
from unique_search_proxy_core.url_safety.settings import url_safety_settings

from unique_search_proxy_client.web.core.provider_response import (
    raise_for_upstream_response,
    transport_error_raw,
)
from unique_search_proxy_client.web.core.search_engines.service_base import (
    SearchEngineService,
)

_LOGGER = logging.getLogger(__name__)
_CUSTOM_API_PROVIDER_LABEL = "Custom API"
_MAX_CUSTOM_API_RESPONSE_BYTES = 10 * 1024 * 1024
_FORBIDDEN_REQUEST_HEADERS = frozenset(
    {
        "connection",
        "content-length",
        "host",
        "proxy-authenticate",
        "proxy-authorization",
        "transfer-encoding",
        "upgrade",
    }
)


def _parse_json_object(value: str, *, field_name: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise BadRequestProxyError(
            f"{field_name} must be a valid JSON object",
        ) from exc
    if not isinstance(parsed, dict):
        raise BadRequestProxyError(f"{field_name} must be a JSON object")
    return parsed


def _parse_headers(value: str) -> dict[str, str]:
    parsed = _parse_json_object(value, field_name="apiHeaders")
    if not all(
        isinstance(key, str) and isinstance(item, str) for key, item in parsed.items()
    ):
        raise BadRequestProxyError("apiHeaders keys and values must be strings")
    forbidden = sorted(
        name for name in parsed if name.lower() in _FORBIDDEN_REQUEST_HEADERS
    )
    if forbidden:
        raise BadRequestProxyError(
            "apiHeaders contains fields controlled by Search Proxy",
            details=[{"header": name} for name in forbidden],
        )
    return parsed


def _validate_endpoint(endpoint: str) -> None:
    parsed = urlsplit(endpoint)
    if parsed.username is not None or parsed.password is not None:
        raise BadRequestProxyError(
            "Custom API endpoint credentials must be provided in headers",
        )


class CustomApiSearchService(SearchEngineService[CustomApiSearchRequest]):
    """Tenant-configured API provider with fail-closed outbound URL controls."""

    engine_id = SearchEngineType.CUSTOM_API.value

    @property
    def mode(self) -> str:
        return get_search_engine_mode(SearchEngineType.CUSTOM_API).value

    async def search(
        self,
        request: CustomApiSearchRequest,  # type: ignore[valid-type]
    ) -> tuple[SearchEngineRaw, WebSearchResults]:
        client = self._http_client
        if client is None:
            raise RuntimeError("HTTP client is required for Custom API search")

        if not url_safety_settings.enabled:
            raise ForbiddenTargetError(
                "Custom API is unavailable while URL safety is disabled",
            )
        _validate_endpoint(request.api_endpoint)
        try:
            resolved_target = await UrlSafetyService.resolve_crawl_target(
                request.api_endpoint,
            )
        except CrawlTargetValidationError as exc:
            blocked = exc.blocked_targets[0]
            raise ForbiddenTargetError(
                "Custom API endpoint is blocked by URL safety policy",
                details=[
                    {
                        "category": blocked.category,
                        "reason": blocked.reason,
                    }
                ],
            ) from exc

        request_url, pin_headers, extensions = pinned_httpx_get_args(resolved_target)
        headers = _parse_headers(request.api_headers)
        headers.update(pin_headers)
        params = _parse_json_object(
            request.api_additional_query_params,
            field_name="apiAdditionalQueryParams",
        )
        body = _parse_json_object(
            request.api_additional_body_params,
            field_name="apiAdditionalBodyParams",
        )
        if request.api_request_method == CustomApiRequestMethod.GET:
            params["query"] = request.query
        else:
            body["query"] = request.query

        try:
            async with client.stream(
                method=request.api_request_method.value,
                url=request_url,
                headers=headers,
                params=params,
                json=body,
                extensions=extensions or None,
                timeout=request.timeout,
                follow_redirects=False,
            ) as streaming_response:
                chunks: list[bytes] = []
                response_size = 0
                async for chunk in streaming_response.aiter_bytes():
                    response_size += len(chunk)
                    if response_size > _MAX_CUSTOM_API_RESPONSE_BYTES:
                        raise UpstreamError(
                            "Custom API response exceeded the size limit",
                        )
                    chunks.append(chunk)
                response = httpx.Response(
                    status_code=streaming_response.status_code,
                    headers=streaming_response.headers,
                    content=b"".join(chunks),
                    request=streaming_response.request,
                )
        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError(
                f"Custom API search timed out after {request.timeout}s",
                upstream_raw=transport_error_raw(exc),
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(
                "Custom API search request failed",
                upstream_raw=transport_error_raw(exc),
            ) from exc

        if response.is_redirect:
            raise ForbiddenTargetError("Custom API redirects are not allowed")
        raise_for_upstream_response(
            response,
            provider_label=_CUSTOM_API_PROVIDER_LABEL,
        )

        try:
            payload = response.json()
        except ValueError as exc:
            raise UpstreamError("Custom API returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise UpstreamError("Custom API response must be a JSON object")

        try:
            curated = WebSearchResults.model_validate(payload)
        except ValidationError as exc:
            raise UpstreamError("Custom API returned an invalid result schema") from exc

        _LOGGER.info("Custom API search returned %s curated results", len(curated))
        return SearchEngineRaw(pages=[payload]), curated


__all__ = ["CustomApiSearchService"]
