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
    SearchEngine,
    SearchEngineType,
    get_search_engine_mode,
)
from unique_search_proxy_core.search_engines.google.schema import (
    GoogleConfig,
    GoogleRequest,
)
from unique_search_proxy_core.search_engines.pagination import (
    DEFAULT_MAX_PAGE_SIZE,
    PageRequest,
    iter_page_requests,
)

from unique_search_proxy_client.web.core.search_engines.google.credentials import (
    GoogleCredentials,
    build_google_query_params,
)

_LOGGER = logging.getLogger(__name__)


class GoogleSearchService(SearchEngine[GoogleRequest]):
    """Google Custom Search JSON API provider."""

    engine_id = SearchEngineType.GOOGLE.value

    @property
    def snippet_only(self) -> bool:
        return True

    @property
    def mode(self) -> str:
        return get_search_engine_mode(SearchEngineType.GOOGLE).value

    async def search(
        self,
        request: GoogleRequest,  # type: ignore
    ) -> tuple[SearchEngineRaw, WebSearchResults]:
        credentials = GoogleCredentials.from_env(
            search_engine_id=request.search_engine_id,
        )
        fetch_size = request.fetch_size
        timeout = request.timeout

        raw_pages = SearchEngineRaw(pages=[])
        curated = WebSearchResults(results=[])

        for page_request in iter_page_requests(
            fetch_size,
            max_page_size=DEFAULT_MAX_PAGE_SIZE,
        ):
            page = await self._fetch_page(
                request=request,
                credentials=credentials,
                page=page_request,
                timeout=timeout,
            )
            raw_pages.append(page)
            page_results = self._extract_results(page)
            if not page_results:
                if not len(curated.results):
                    raise EmptySearchResultsError(
                        f"Google search returned no results for query {request.query!r}",
                        engine=SearchEngineType.GOOGLE.value,
                    )
                break
            curated = curated.extend(page_results)

        curated = curated.dedupe()

        _LOGGER.info("Google search returned %s curated results", len(curated))
        return raw_pages, curated

    async def _fetch_page(
        self,
        *,
        request: GoogleRequest,  # type: ignore
        credentials: GoogleCredentials,
        page: PageRequest,
        timeout: int,
    ) -> dict[str, Any]:
        params = build_google_query_params(
            query=request.query,
            credentials=credentials,
            request=request,
            page=page,
        )

        client = self._http_client
        if client is None:
            raise RuntimeError("HTTP client is required for Google search")

        try:
            response = await client.get(
                credentials.api_endpoint,
                params=params,
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError(
                f"Google search timed out after {timeout}s",
                engine=SearchEngineType.GOOGLE.value,
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(
                f"Google search request failed: {exc}",
                engine=SearchEngineType.GOOGLE.value,
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
                "Google Custom Search API rate limit exceeded",
                engine=SearchEngineType.GOOGLE.value,
                retry_after_seconds=retry_after,
            )

        message = f"Google Custom Search API returned HTTP {response.status_code}"
        try:
            payload = response.json()
            error_message = payload.get("error", {}).get("message")
            if error_message:
                message = f"{message}: {error_message}"
        except Exception:
            pass

        raise UpstreamError(message, engine=SearchEngineType.GOOGLE.value)

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
