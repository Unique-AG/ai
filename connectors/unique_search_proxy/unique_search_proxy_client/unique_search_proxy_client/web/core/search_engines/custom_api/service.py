from __future__ import annotations

import json
import logging
from typing import Any

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
    url_safety_settings,
)

from unique_search_proxy_client.web.core.provider_response import (
    raise_for_upstream_response,
    transport_error_raw,
)
from unique_search_proxy_client.web.core.search_engines.service_base import (
    SearchEngineService,
)

_LOGGER = logging.getLogger(__name__)
_CUSTOM_API_PROVIDER_LABEL = "Custom API"


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
    return parsed


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

        # Admin configuration must not grant access to unapproved private targets.
        try:
            resolved_target = await UrlSafetyService.resolve_custom_api_target(
                request.api_endpoint,
                trusted_private_hosts=(
                    url_safety_settings.custom_api_trusted_private_hosts
                ),
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
            response = await client.request(
                method=request.api_request_method.value,
                url=request_url,
                headers=headers,
                params=params,
                json=body,
                extensions=extensions or None,
                timeout=request.timeout,
                follow_redirects=False,
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
