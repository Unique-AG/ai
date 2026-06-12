from __future__ import annotations

import logging
from typing import Any

import httpx
from httpx import Response
from unique_search_proxy_core.errors import (
    EmptySearchResultsError,
    RateLimitedError,
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
from unique_search_proxy_core.search_engines.brave.schema import (
    BraveConfig,
    BraveSearchRequest,
)

from unique_search_proxy_client.web.core.search_engines.brave.pagination import (
    iter_brave_page_requests,
)
from unique_search_proxy_client.web.core.search_engines.brave.query_params import (
    build_brave_query_params,
)
from unique_search_proxy_client.web.core.search_engines.pagination import PageRequest
from unique_search_proxy_client.web.core.search_engines.service_base import (
    SearchEngineService,
)
from unique_search_proxy_client.web.settings.providers.brave import (
    brave_search_credentials as credentials,
)

_LOGGER = logging.getLogger(__name__)


class BraveSearchService(SearchEngineService[BraveSearchRequest]):
    """Brave Web Search API provider."""

    engine_id = SearchEngineType.BRAVE.value

    @property
    def mode(self) -> str:
        return get_search_engine_mode(SearchEngineType.BRAVE).value

    async def search(
        self,
        request: BraveSearchRequest,  # type: ignore
    ) -> tuple[SearchEngineRaw, WebSearchResults]:
        credentials.check_credentials()

        fetch_size = request.fetch_size
        timeout = request.timeout

        raw_pages = SearchEngineRaw(pages=[])
        curated = WebSearchResults(results=[])

        for page_request in iter_brave_page_requests(fetch_size):
            if len(curated.results) >= fetch_size:
                break
            page = await self._fetch_page(
                request=request,
                api_key=credentials.api_key,
                api_endpoint=credentials.api_endpoint,
                page=page_request,
                timeout=timeout,
            )
            raw_pages.append(page)
            page_results = self._extract_web_results(page)
            if not page_results:
                if not len(curated.results):
                    raise EmptySearchResultsError(
                        f"Brave search returned no results for query {request.query!r}",
                    )
                break
            curated = curated.extend(page_results)
            if len(curated.results) >= fetch_size:
                break
            if not _more_results_available(page):
                break

        curated = curated.dedupe()
        curated = WebSearchResults(results=curated.results[:fetch_size])

        _LOGGER.info("Brave search returned %s curated results", len(curated))
        return raw_pages, curated

    async def _fetch_page(
        self,
        *,
        request: BraveSearchRequest,  # type: ignore
        api_key: str,
        api_endpoint: str,
        page: PageRequest,
        timeout: int,
    ) -> dict[str, Any]:
        params = build_brave_query_params(
            query=request.query,
            request=request,
            page=page,
        )

        client = self._http_client
        if client is None:
            raise RuntimeError("HTTP client is required for Brave search")

        try:
            response = await client.get(
                api_endpoint,
                params=params,
                headers=_brave_headers(api_key),
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError(
                f"Brave search timed out after {timeout}s",
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(
                f"Brave search request failed: {exc}",
            ) from exc

        self._raise_for_response(response)
        return response.json()

    def _raise_for_response(self, response: Response) -> None:
        if response.is_success:
            return

        if response.status_code == 429:
            retry_after_raw = response.headers.get("Retry-After")
            retry_after: int | None = None
            if retry_after_raw is not None:
                try:
                    retry_after = int(retry_after_raw)
                except ValueError:
                    retry_after = None
            raise RateLimitedError(
                "Brave Web Search API rate limit exceeded",
                retry_after_seconds=retry_after,
            )

        message = f"Brave Web Search API returned HTTP {response.status_code}"
        try:
            payload = response.json()
            error_message = payload.get("message")
            if error_message:
                message = f"{message}: {error_message}"
        except Exception:
            pass

        raise UpstreamError(message)

    def _extract_web_results(self, payload: dict[str, Any]) -> list[WebSearchResult]:
        web = payload.get("web")
        if not isinstance(web, dict):
            return []

        items: list[dict[str, Any]] = web.get("results") or []
        results: list[WebSearchResult] = []
        for item in items:
            url = item.get("url") or ""
            results.append(
                WebSearchResult(
                    url=url.strip() if url else "",
                    title=item.get("title") or "",
                    snippet=_build_snippet(item),
                ),
            )
        return results

    @staticmethod
    def llm_call_schema(
        config: BraveConfig,
        *,
        strict_required: bool = True,
    ) -> type[Any]:
        from unique_search_proxy_core.projection import build_llm_call_model

        return build_llm_call_model(
            BraveConfig,
            config,
            strict_required=strict_required,
        )


def _brave_headers(api_key: str) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }


def _more_results_available(payload: dict[str, Any]) -> bool:
    query = payload.get("query")
    if isinstance(query, dict):
        return bool(query.get("more_results_available"))
    return False


def _build_snippet(item: dict[str, Any]) -> str:
    main_snippet = item.get("description") or ""
    extra_snippets = item.get("extra_snippets") or []
    if not extra_snippets:
        return main_snippet
    return "\n".join([main_snippet, *extra_snippets])
