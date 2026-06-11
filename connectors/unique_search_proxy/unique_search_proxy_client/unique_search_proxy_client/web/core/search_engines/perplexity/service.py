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
from unique_search_proxy_core.search_engines.perplexity.schema import (
    PerplexityConfig,
    PerplexityRequest,
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

_LOGGER = logging.getLogger(__name__)


class PerplexitySearchService(SearchEngineService[PerplexityRequest]):
    """Perplexity Search API provider."""

    engine_id = SearchEngineType.PERPLEXITY.value

    @property
    def mode(self) -> str:
        return get_search_engine_mode(SearchEngineType.PERPLEXITY).value

    async def search(
        self,
        request: PerplexityRequest,  # type: ignore
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
                headers=_perplexity_headers(credentials.api_key),
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError(
                f"Perplexity search timed out after {timeout}s",
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(
                f"Perplexity search request failed: {exc}",
            ) from exc

        self._raise_for_response(response)
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
                "Perplexity Search API rate limit exceeded",
                retry_after_seconds=retry_after,
            )

        message = f"Perplexity Search API returned HTTP {response.status_code}"
        try:
            payload = response.json()
            error = payload.get("error")
            if isinstance(error, dict):
                detail = error.get("detail") or error.get("message")
                if detail:
                    message = f"{message}: {detail}"
            elif isinstance(error, str):
                message = f"{message}: {error}"
        except Exception:
            pass

        raise UpstreamError(message)

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

    @staticmethod
    def llm_call_schema(
        config: PerplexityConfig,
        *,
        strict_required: bool = True,
    ) -> type[Any]:
        from unique_search_proxy_core.projection import build_llm_call_model

        return build_llm_call_model(
            PerplexityConfig,
            config,
            strict_required=strict_required,
        )


def _perplexity_headers(api_key: str) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
