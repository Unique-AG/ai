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
    SearchResponse,
    WebSearchResult,
    WebSearchResults,
)
from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_search_proxy_core.search_engines.config_types import SearchRequest

from unique_search_proxy_client.web.api.v1.openapi_examples import (
    SEARCH_OPENAPI_EXAMPLES,
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
    body: SearchRequest = Body(openapi_examples=SEARCH_OPENAPI_EXAMPLES),  # type: ignore[valid-type]
) -> SearchResponse:
    engine = body.engine
    engine_id = engine.value if hasattr(engine, "value") else str(engine)
    timeout = body.timeout
    started = time.perf_counter()

    try:
        pool = get_http_client_pool(request.app)
        engine = get_search_engine_service(
            SearchEngineType(engine_id) if isinstance(engine, str) else engine,
            http_client=pool.client,
        )
        async with asyncio.timeout(timeout):
            raw, curated = await engine.search(body)
    except TimeoutError as exc:
        record_search_error(
            engine_id,
            ProxyErrorCode.UPSTREAM_TIMEOUT.value,
            time.perf_counter() - started,
        )
        raise UpstreamTimeoutError(
            f"Search engine '{engine_id}' timed out after {timeout}s",
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
        query=body.query,
        raw=raw,
        curated=_curated_results(curated),
    )
