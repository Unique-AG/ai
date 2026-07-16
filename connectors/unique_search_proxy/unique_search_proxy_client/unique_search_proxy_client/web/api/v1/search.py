from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, Body, Request
from unique_search_proxy_core.errors import (
    ProxyError,
    UpstreamTimeoutError,
    attach_request_context,
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


def _search_request_context(exc: ProxyError, *, engine_id: str) -> ProxyError:
    return attach_request_context(
        exc,
        request="search",
        provider=engine_id,
    )


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
    _LOGGER.info("search start engine=%s timeout=%ss", engine_id, timeout)
    _LOGGER.debug("search query=%r", body.query)

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
        _LOGGER.warning(
            "search timeout engine=%s timeout=%ss duration=%.0fms",
            engine_id,
            timeout,
            (time.perf_counter() - started) * 1000,
        )
        raise _search_request_context(
            UpstreamTimeoutError(
                f"Search engine '{engine_id}' timed out after {timeout}s",
            ),
            engine_id=engine_id,
        ) from exc
    except ProxyError as exc:
        _LOGGER.warning(
            "search failed engine=%s code=%s duration=%.0fms",
            engine_id,
            exc.code.value if hasattr(exc.code, "value") else exc.code,
            (time.perf_counter() - started) * 1000,
        )
        raise _search_request_context(exc, engine_id=engine_id) from exc
    except Exception:
        record_search_error(
            engine_id,
            "INTERNAL_ERROR",
            time.perf_counter() - started,
        )
        _LOGGER.exception(
            "search error engine=%s duration=%.0fms",
            engine_id,
            (time.perf_counter() - started) * 1000,
        )
        raise

    duration = time.perf_counter() - started
    record_search_success(engine_id, duration)
    curated = _curated_results(curated)
    _LOGGER.info(
        "search success engine=%s results=%d duration=%.0fms",
        engine_id,
        len(curated),
        duration * 1000,
    )

    return SearchResponse(
        engine=engine_id,
        query=body.query,
        raw=raw,
        curated=curated,
    )
