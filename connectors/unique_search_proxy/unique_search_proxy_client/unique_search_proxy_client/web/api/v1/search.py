from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, Body, Request
from unique_search_proxy_core.errors import (
    ProxyError,
    UpstreamTimeoutError,
)
from unique_search_proxy_core.schema import (
    ProxyErrorCode,
    WebSearchResult,
    WebSearchResults,
)
from unique_search_proxy_core.search_engines.params import call_query

from unique_search_proxy_client.web.api.v1.openapi_examples import (
    SEARCH_OPENAPI_EXAMPLES,
)
from unique_search_proxy_client.web.api.v1.schema import (
    SearchRequest,
    SearchResponse,
)
from unique_search_proxy_client.web.core.client import get_http_client_pool
from unique_search_proxy_client.web.core.search_engines import (
    get_search_engine_service,
)
from unique_search_proxy_client.web.monitoring.metrics import (
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


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Run a search engine with a typed call payload",
)
async def search(
    request: Request,
    body: SearchRequest = Body(openapi_examples=SEARCH_OPENAPI_EXAMPLES),  # type: ignore
) -> SearchResponse:
    engine_id = body.engine.value
    started = time.perf_counter()

    try:
        pool = get_http_client_pool(request.app)
        engine = get_search_engine_service(body.engine, http_client=pool.client)
        async with asyncio.timeout(body.timeout):
            raw, curated = await engine.search(body, timeout=body.timeout)
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

    duration = time.perf_counter() - started
    record_search_success(engine_id, duration)

    return SearchResponse(
        engine=engine_id,
        query=call_query(body),
        raw=raw,
        curated=_curated_results(curated),
    )
