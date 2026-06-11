from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, Body, Request
from unique_search_proxy_core.crawlers.config_types import CrawlRequest
from unique_search_proxy_core.errors import ProxyError, UpstreamTimeoutError
from unique_search_proxy_core.schema import CrawlResponse, ProxyErrorCode

from unique_search_proxy_client.web.api.v1.openapi_examples import (
    CRAWL_OPENAPI_EXAMPLES,
)
from unique_search_proxy_client.web.core.client import get_http_client_pool
from unique_search_proxy_client.web.core.crawlers.factory import get_crawler_service
from unique_search_proxy_client.web.monitoring.metrics import (
    record_crawl_error,
    record_crawl_success,
)

router = APIRouter(tags=["crawl"])
_LOGGER = logging.getLogger(__name__)


@router.post(
    "/crawl",
    response_model=CrawlResponse,
    summary="Crawl URLs with a configured crawler",
)
async def crawl(
    request: Request,
    body: CrawlRequest = Body(openapi_examples=CRAWL_OPENAPI_EXAMPLES),  # type: ignore[valid-type]
) -> CrawlResponse:
    crawler_id = body.crawler
    timeout = body.timeout
    started = time.perf_counter()

    try:
        pool = get_http_client_pool(request.app)
        crawler = get_crawler_service(crawler_id, http_client=pool.client)
        async with asyncio.timeout(timeout):
            results = await crawler.crawl(body)
    except TimeoutError as exc:
        record_crawl_error(
            crawler_id,
            ProxyErrorCode.UPSTREAM_TIMEOUT.value,
            time.perf_counter() - started,
        )
        raise UpstreamTimeoutError(
            f"Crawler '{crawler_id}' timed out after {timeout}s",
            crawler=crawler_id,
        ) from exc
    except ProxyError:
        raise
    except Exception:
        record_crawl_error(
            crawler_id,
            "INTERNAL_ERROR",
            time.perf_counter() - started,
        )
        raise

    record_crawl_success(crawler_id, len(body.urls), time.perf_counter() - started)
    return CrawlResponse(crawler=crawler_id, results=results)
