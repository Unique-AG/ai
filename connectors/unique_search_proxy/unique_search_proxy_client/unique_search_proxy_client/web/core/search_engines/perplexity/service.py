from __future__ import annotations

import logging
from typing import Any

import httpx
from unique_search_proxy_core.errors import (
    EmptySearchResultsError,
    UpstreamError,
    UpstreamTimeoutError,
)
from unique_search_proxy_core.schema import (
    SearchEngineRaw,
    WebSearchResult,
    WebSearchResults,
)
from unique_search_proxy_core.search_engines.base import (
    SearchEngineType,
    get_search_engine_mode,
)
from unique_search_proxy_core.search_engines.perplexity.schema import (
    PerplexitySearchRequest,
)

from unique_search_proxy_client.web.core.provider_response import (
    raise_for_upstream_response,
    transport_error_raw,
)
from unique_search_proxy_client.web.core.search_engines.perplexity.request_body import (
    build_perplexity_request_body,
)
from unique_search_proxy_client.web.core.search_engines.service_base import (
    SearchEngineService,
)
from unique_search_proxy_client.web.settings.providers import (
    perplexity_search_credentials as credentials,
)
from unique_search_proxy_client.web.settings.secret_str import read_secret

_LOGGER = logging.getLogger(__name__)
_PERPLEXITY_PROVIDER_LABEL = "Perplexity Search API"


class PerplexitySearchService(SearchEngineService[PerplexitySearchRequest]):
    """Perplexity Search API provider."""

    engine_id = SearchEngineType.PERPLEXITY.value

    @property
    def mode(self) -> str:
        return get_search_engine_mode(SearchEngineType.PERPLEXITY).value

    async def search(
        self,
        request: PerplexitySearchRequest,  # type: ignore
    ) -> tuple[SearchEngineRaw, WebSearchResults]:
        credentials.check_credentials()

        timeout = request.timeout
        body = build_perplexity_request_body(query=request.query, request=request)

        client = self._http_client
        if client is None:
            raise RuntimeError("HTTP client is required for Perplexity search")

        try:
            response = await client.post(
                credentials.api_endpoint,
                json=body,
                headers=_perplexity_headers(read_secret(credentials.api_key)),
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError(
                f"Perplexity search timed out after {timeout}s",
                upstream_raw=transport_error_raw(exc),
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(
                f"Perplexity search request failed: {exc}",
                upstream_raw=transport_error_raw(exc),
            ) from exc

        raise_for_upstream_response(
            response,
            provider_label=_PERPLEXITY_PROVIDER_LABEL,
            detail_keys=("error", "message", "detail"),
            nested_error_keys=("detail", "message"),
            rate_limited_message=f"{_PERPLEXITY_PROVIDER_LABEL} rate limit exceeded",
        )
        payload = response.json()
        raw_pages = SearchEngineRaw(pages=[payload])
        curated = WebSearchResults(results=self._extract_results(payload))
        if not curated.results:
            raise EmptySearchResultsError(
                f"Perplexity search returned no results for query {request.query!r}",
            )

        curated = curated.dedupe()
        curated = WebSearchResults(results=curated.results[: request.fetch_size])

        _LOGGER.info("Perplexity search returned %s curated results", len(curated))
        return raw_pages, curated

    def _extract_results(self, payload: dict[str, Any]) -> list[WebSearchResult]:
        items = payload.get("results") or []
        results: list[WebSearchResult] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            url = item.get("url") or ""
            results.append(
                WebSearchResult(
                    url=url.strip() if url else "",
                    title=item.get("title") or "",
                    snippet=item.get("snippet") or "",
                ),
            )
        return results


def _perplexity_headers(api_key: str) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
