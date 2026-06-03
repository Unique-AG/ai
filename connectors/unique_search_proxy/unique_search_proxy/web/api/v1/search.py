from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter, Body, Request

from unique_search_proxy.web.api.v1.openapi_examples import (
    SEARCH_CALL_SCHEMA_OPENAPI_EXAMPLES,
    SEARCH_OPENAPI_EXAMPLES,
)
from unique_search_proxy.web.api.v1.schema import (
    SearchCallSchemaRequest,
    SearchCallSchemaResponse,
    SearchRequest,
    SearchResponse,
)
from unique_search_proxy.web.core.client import get_http_client_pool
from unique_search_proxy.web.core.crawlers.factory import get_crawler_service
from unique_search_proxy.web.core.errors import (
    ProxyError,
    UpstreamTimeoutError,
    ValidationProxyError,
)
from unique_search_proxy.web.core.schema import (
    ProxyErrorCode,
    WebSearchResult,
    WebSearchResults,
)
from unique_search_proxy.web.core.search_engines import (
    get_search_engine_service,
    resolve_engine_call,
)
from unique_search_proxy.web.core.search_engines.call_schema import (
    resolve_search_call_schema,
)
from unique_search_proxy.web.core.search_engines.params import call_query
from unique_search_proxy.web.monitoring.metrics import (
    record_search_error,
    record_search_success,
)

router = APIRouter(tags=["search"])
_LOGGER = logging.getLogger(__name__)


def _curated_results(
    curated: WebSearchResults | list[WebSearchResult],
) -> list[WebSearchResult]:
    if isinstance(curated, WebSearchResults):
        return curated.results
    return curated


async def _fill_content_from_crawler(
    *,
    results: list[WebSearchResult],
    crawler_config: Any,
    http_client: Any,
    timeout: int,
) -> list[WebSearchResult]:
    urls = [result.url for result in results if result.url]
    if not urls:
        return results

    crawler = get_crawler_service(crawler_config, http_client=http_client)
    crawl_outcomes = await crawler.crawl(urls, timeout=timeout)
    content_by_url = {
        outcome.url: outcome.content or ""
        for outcome in crawl_outcomes
        if outcome.error is None and outcome.content
    }

    filled: list[WebSearchResult] = []
    for result in results:
        content = content_by_url.get(result.url, result.content)
        filled.append(
            WebSearchResult(
                url=result.url,
                title=result.title,
                snippet=result.snippet,
                content=content,
            ),
        )
    return filled


@router.post(
    "/search/call-schema",
    response_model=SearchCallSchemaResponse,
    summary="JSON Schema for SearchRequest.call",
)
async def search_call_schema(
    body: SearchCallSchemaRequest = Body(
        openapi_examples=SEARCH_CALL_SCHEMA_OPENAPI_EXAMPLES,
    ),
) -> SearchCallSchemaResponse:
    descriptor = resolve_search_call_schema(body.config)
    return SearchCallSchemaResponse(
        engine=descriptor.engine,
        mode=descriptor.mode,
        snippet_only=descriptor.snippet_only,
        call_schema=descriptor.call_schema,
    )


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Run a configured search engine",
)
async def search(
    request: Request,
    body: SearchRequest = Body(openapi_examples=SEARCH_OPENAPI_EXAMPLES),
) -> SearchResponse:
    engine_id = body.config.engine.value
    started = time.perf_counter()
    call = resolve_engine_call(body.config, body.call)

    try:
        pool = get_http_client_pool(request.app)
        engine = get_search_engine_service(body.config, http_client=pool.client)
        if body.include_content and engine.snippet_only and body.crawler_config is None:
            raise ValidationProxyError(
                "crawlerConfig is required when includeContent is true "
                "for snippet-only engines",
            )
        async with asyncio.timeout(body.timeout):
            raw, curated = await engine.search(call, timeout=body.timeout)
    except TimeoutError as exc:
        record_search_error(
            engine_id,
            ProxyErrorCode.UPSTREAM_TIMEOUT.value,
            time.perf_counter() - started,
        )
        raise UpstreamTimeoutError(
            f"Search engine '{engine_id}' timed out after {body.timeout}s",
            engine=engine_id,
        ) from exc
    except ProxyError:
        raise
    except Exception:
        record_search_error(
            engine_id,
            "INTERNAL_ERROR",
            time.perf_counter() - started,
        )
        raise

    curated_list = _curated_results(curated)

    if body.include_content and engine.snippet_only:
        curated_list = await _fill_content_from_crawler(
            results=curated_list,
            crawler_config=body.crawler_config,
            http_client=pool.client,
            timeout=body.timeout,
        )

    duration = time.perf_counter() - started
    record_search_success(engine_id, duration)

    query = call_query(call)

    return SearchResponse(
        engine=engine_id,
        query=query,
        raw=raw,
        curated=curated_list,
    )
