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
from unique_search_proxy_core.search_engines.google.schema import (
    GoogleConfig,
    GoogleSearchRequest,
)

from unique_search_proxy_client.web.core.provider_response import (
    raise_for_upstream_response,
    transport_error_raw,
)
from unique_search_proxy_client.web.core.search_engines.google.pagination import (
    iter_google_page_requests,
)
from unique_search_proxy_client.web.core.search_engines.google.query_params import (
    build_google_query_params,
)
from unique_search_proxy_client.web.core.search_engines.pagination import PageRequest
from unique_search_proxy_client.web.core.search_engines.service_base import (
    SearchEngineService,
)
from unique_search_proxy_client.web.settings.providers import (
    google_search_credentials as credentials,
)

_GOOGLE_PROVIDER_LABEL = "Google Custom Search API"

_LOGGER = logging.getLogger(__name__)


class GoogleSearchService(SearchEngineService[GoogleSearchRequest]):
    """Google Custom Search JSON API provider."""

    engine_id = SearchEngineType.GOOGLE.value

    @property
    def mode(self) -> str:
        return get_search_engine_mode(SearchEngineType.GOOGLE).value

    async def search(
        self,
        request: GoogleSearchRequest,  # type: ignore
    ) -> tuple[SearchEngineRaw, WebSearchResults]:
        credentials.check_credentials()
        search_engine_id = credentials.engine_id

        fetch_size = request.fetch_size
        timeout = request.timeout

        raw_pages = SearchEngineRaw(pages=[])
        curated = WebSearchResults(results=[])

        for page_request in iter_google_page_requests(fetch_size):
            page = await self._fetch_page(
                request=request,
                api_key=credentials.api_key,
                search_engine_id=search_engine_id,
                api_endpoint=credentials.api_endpoint,
                page=page_request,
                timeout=timeout,
            )
            raw_pages.append(page)
            page_results = self._extract_results(page)
            if not page_results:
                if not len(curated.results):
                    raise EmptySearchResultsError(
                        f"Google search returned no results for query {request.query!r}",
                    )
                break
            curated = curated.extend(page_results)

        curated = curated.dedupe()

        _LOGGER.info("Google search returned %s curated results", len(curated))
        return raw_pages, curated

    async def _fetch_page(
        self,
        *,
        request: GoogleSearchRequest,  # type: ignore
        api_key: str,
        search_engine_id: str,
        api_endpoint: str,
        page: PageRequest,
        timeout: int,
    ) -> dict[str, Any]:
        params = build_google_query_params(
            query=request.query,
            api_key=api_key,
            search_engine_id=search_engine_id,
            request=request,
            page=page,
        )

        client = self._http_client
        if client is None:
            raise RuntimeError("HTTP client is required for Google search")

        try:
            response = await client.get(
                api_endpoint,
                params=params,
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError(
                f"Google search timed out after {timeout}s",
                upstream_raw=transport_error_raw(exc),
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(
                f"Google search request failed: {exc}",
                upstream_raw=transport_error_raw(exc),
            ) from exc

        raise_for_upstream_response(
            response,
            provider_label=_GOOGLE_PROVIDER_LABEL,
            detail_keys=("error",),
            nested_error_keys=("message",),
            rate_limited_message=f"{_GOOGLE_PROVIDER_LABEL} rate limit exceeded",
        )
        return response.json()

    def _extract_results(self, payload: dict[str, Any]) -> list[WebSearchResult]:
        items = payload.get("items") or []
        results: list[WebSearchResult] = []
        for item in items:
            link = item.get("link") or ""
            results.append(
                WebSearchResult(
                    url=link.strip() if link else "",
                    title=item.get("title") or item.get("htmlTitle") or "",
                    snippet=item.get("snippet", ""),
                ),
            )
        return results

    @staticmethod
    def llm_call_schema(
        config: GoogleConfig,
        *,
        strict_required: bool = True,
    ) -> type[Any]:

        from unique_search_proxy_core.projection import build_llm_call_model

        return build_llm_call_model(
            GoogleConfig,
            config,
            strict_required=strict_required,
        )
