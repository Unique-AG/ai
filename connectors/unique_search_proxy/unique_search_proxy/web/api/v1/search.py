from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, Request

from unique_search_proxy.web.api.v1.schema import SearchRequest, SearchResponse
from unique_search_proxy.web.core.client import get_http_client_pool
from unique_search_proxy.web.core.errors import ProxyError, UpstreamTimeoutError
from unique_search_proxy.web.core.registry import get_search_engine
from unique_search_proxy.web.core.schema import ProxyErrorCode
from unique_search_proxy.web.monitoring.metrics import (
    record_search_error,
    record_search_success,
)

router = APIRouter(tags=["search"])
_LOGGER = logging.getLogger(__name__)


@router.post("/search", response_model=SearchResponse)
async def search(request: Request, body: SearchRequest) -> SearchResponse:
    engine_id = body.config.engine
    started = time.perf_counter()

    try:
        engine_cls = get_search_engine(engine_id)
        _ = get_http_client_pool(request.app)

        engine = engine_cls(body.config)
        async with asyncio.timeout(body.timeout):
            raw, curated = await engine.search(
                body.query,
                fetch_size=body.fetch_size,
                timeout=body.timeout,
            )
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
        query=body.query,
        raw=raw,
        curated=curated,
    )
