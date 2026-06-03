from __future__ import annotations

import logging
from typing import Any

import httpx
from httpx import AsyncClient, Response
from pydantic import BaseModel

from unique_search_proxy.web.core.errors import (
    EmptySearchResultsError,
    RateLimitedError,
    UpstreamError,
    UpstreamTimeoutError,
)
from unique_search_proxy.web.core.schema import (
    SearchEngineRaw,
    WebSearchResult,
    WebSearchResults,
)
from unique_search_proxy.web.core.search_engines.base import (
    SearchEngine,
    SearchEngineType,
    get_search_engine_mode,
)
from unique_search_proxy.web.core.search_engines.google.schema import (
    GoogleConfig,
    GoogleCredentials,
    GoogleSearchCall,
    build_google_query_params,
)
from unique_search_proxy.web.core.search_engines.pagination import (
    DEFAULT_MAX_PAGE_SIZE,
    PageRequest,
    iter_page_requests,
)
from unique_search_proxy.web.core.utils.content import (
    canonicalize_url,
)

_LOGGER = logging.getLogger(__name__)


class GoogleSearchService(SearchEngine[GoogleConfig, GoogleSearchCall]):
    """Google Custom Search JSON API provider."""

    engine_id = SearchEngineType.GOOGLE.value

    def __init__(
        self,
        config: GoogleConfig,
        *,
        http_client: AsyncClient | None = None,
    ) -> None:
        super().__init__(config, http_client=http_client)

    @property
    def snippet_only(self) -> bool:
        return True

    @property
    def mode(self) -> str:
        return get_search_engine_mode(SearchEngineType.GOOGLE).value

    async def search(
        self,
        call: GoogleSearchCall,
        *,
        timeout: int,
    ) -> tuple[SearchEngineRaw, WebSearchResults]:
        credentials = GoogleCredentials.from_env(
            search_engine_id=self.config.search_engine_id,
        )
        fetch_size = self.config.fetch_size

        raw_pages = SearchEngineRaw(pages=[])
        curated = WebSearchResults(results=[])

        for page_request in iter_page_requests(
            fetch_size,
            max_page_size=DEFAULT_MAX_PAGE_SIZE,
        ):
            page = await self._fetch_page(
                call=call,
                credentials=credentials,
                page=page_request,
                timeout=timeout,
            )
            raw_pages.append(page)
            page_results = self._extract_results(page)
            if not page_results:
                if not curated:
                    raise EmptySearchResultsError(
                        f"Google search returned no results for query {call.query!r}",
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
        call: GoogleSearchCall,
        credentials: GoogleCredentials,
        page: PageRequest,
        timeout: int,
    ) -> dict[str, Any]:
        params = build_google_query_params(
            query=call.query,
            credentials=credentials,
            engine=call,
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
                    url=canonicalize_url(link) if link else "",
                    title=item.get("title") or item.get("htmlTitle") or "",
                    snippet=item.get("snippet", ""),
                ),
            )
        return results

    @staticmethod
    def llm_call_schema(config: GoogleConfig) -> type[BaseModel]:
        from unique_search_proxy.web.core.projection import project_call_schema

        return project_call_schema(
            GoogleSearchCall,
            config.llm_field_names(),
        )
