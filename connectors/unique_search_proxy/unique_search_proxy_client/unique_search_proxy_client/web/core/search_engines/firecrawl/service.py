"""Firecrawl search provider for the Search Proxy."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from itertools import zip_longest
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
from unique_search_proxy_core.search_engines.firecrawl.schema import (
    FIRECRAWL_SOURCES,
    FirecrawlSearchRequest,
)

from unique_search_proxy_client.web.core.provider_response import (
    raise_for_upstream_response,
    transport_error_raw,
)
from unique_search_proxy_client.web.core.search_engines.firecrawl.request_body import (
    build_firecrawl_search_body,
    is_excluded_url,
)
from unique_search_proxy_client.web.core.search_engines.service_base import (
    SearchEngineService,
)
from unique_search_proxy_client.web.settings.providers import (
    firecrawl_crawl_credentials as credentials,
)
from unique_search_proxy_client.web.settings.secret_str import read_secret

_LOGGER = logging.getLogger(__name__)
_FIRECRAWL_PROVIDER_LABEL = "Firecrawl Search API"
# Firecrawl enforces the body ``timeout`` itself; the HTTP client waits a little
# longer so Firecrawl's own timeout error reaches us instead of a dropped socket.
_CLIENT_TIMEOUT_MARGIN_SECONDS = 5
# Rejected key, exhausted credits, or a feature (such as zero data retention)
# that Firecrawl has not enabled for the account: the same request fails again.
_NON_RETRYABLE_STATUS_CODES = frozenset({401, 402, 403})


class FirecrawlSearchService(SearchEngineService[FirecrawlSearchRequest]):
    """Firecrawl ``/v2/search`` provider: search, optionally with page scraping."""

    engine_id = SearchEngineType.FIRECRAWL.value

    @property
    def mode(self) -> str:
        return get_search_engine_mode(SearchEngineType.FIRECRAWL).value

    async def search(
        self,
        request: FirecrawlSearchRequest,  # type: ignore
    ) -> tuple[SearchEngineRaw, WebSearchResults]:
        """Search with Firecrawl and map the results.

        Args:
            request (FirecrawlSearchRequest): Merged search request; ``timeout``
                is in seconds.

        Returns:
            tuple[SearchEngineRaw, WebSearchResults]: Firecrawl's payload and at
                most ``fetch_size`` deduplicated results outside the excluded domains.

        Raises:
            UpstreamTimeoutError: When Firecrawl does not answer in time.
            UpstreamError: When the call fails or the answer is not usable.
            EmptySearchResultsError: When no result is left.
        """
        credentials.check_credentials()

        body = build_firecrawl_search_body(
            query=request.query,
            request=request,
            enterprise=credentials.search_enterprise_modes(request.zero_data_retention),
        )
        timeout = request.timeout + _CLIENT_TIMEOUT_MARGIN_SECONDS

        client = self._http_client
        if client is None:
            raise RuntimeError("HTTP client is required for Firecrawl search")

        try:
            response = await client.post(
                credentials.search_endpoint,
                json=body,
                headers=_firecrawl_headers(read_secret(credentials.api_key)),
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError(
                f"Firecrawl search timed out after {timeout}s",
                upstream_raw=transport_error_raw(exc),
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(
                f"Firecrawl search request failed: {exc}",
                upstream_raw=transport_error_raw(exc),
            ) from exc

        raise_for_upstream_response(
            response,
            provider_label=_FIRECRAWL_PROVIDER_LABEL,
            detail_keys=("error", "message", "detail"),
            nested_error_keys=("message", "detail"),
            rate_limited_message=f"{_FIRECRAWL_PROVIDER_LABEL} rate limit exceeded",
            non_retryable_status_codes=_NON_RETRYABLE_STATUS_CODES,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise UpstreamError("Firecrawl search returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise UpstreamError("Firecrawl search response must be a JSON object")
        if payload.get("success") is False:
            raise UpstreamError(
                f"Firecrawl search failed: {payload.get('error') or 'unknown error'}",
            )

        raw_pages = SearchEngineRaw(pages=[payload])
        # An include list replaces ``excludeDomains`` in the body, so excluded
        # subdomains of an included host are dropped here.
        curated = WebSearchResults(
            results=[
                result
                for result in _extract_results(
                    payload, FIRECRAWL_SOURCES[request.sources]
                )
                if not is_excluded_url(result.url, request.exclude_domains)
            ]
        )
        if not curated.results:
            raise EmptySearchResultsError("Firecrawl search returned no results")

        curated = curated.dedupe()
        curated = WebSearchResults(results=curated.results[: request.fetch_size])

        _LOGGER.info(
            "Firecrawl search returned %s curated results (credits used: %s)",
            len(curated),
            payload.get("creditsUsed"),
        )
        return raw_pages, curated


def _extract_results(
    payload: dict[str, Any],
    sources: Sequence[str],
) -> list[WebSearchResult]:
    data = payload.get("data") or {}
    if isinstance(data, list):
        data = {"web": data}
    if not isinstance(data, dict):
        return []
    per_source = [
        [result for item in data.get(source) or [] if (result := _to_result(item))]
        for source in sources
    ]
    # Interleave: ``limit`` applies per source, so news appended after a full
    # web list would be cut off by ``fetch_size``.
    return [
        result
        for round_ in zip_longest(*per_source)
        for result in round_
        if result is not None
    ]


def _to_result(item: object) -> WebSearchResult | None:
    if not isinstance(item, dict):
        return None
    metadata = item.get("metadata") or {}
    url = item.get("url") or metadata.get("url") or ""
    if not url:
        return None
    return WebSearchResult(
        url=url.strip(),
        title=item.get("title") or metadata.get("title") or "",
        # News items carry their text in ``description`` too, despite the docs
        # naming it ``snippet``; read both.
        snippet=item.get("description") or item.get("snippet") or "",
        content=item.get("markdown") or "",
    )


def _firecrawl_headers(api_key: str) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
