from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Request

from unique_search_proxy.web.api.v1.schema import CrawlRequest, CrawlResponse
from unique_search_proxy.web.core.client import get_http_client_pool
from unique_search_proxy.web.core.errors import ProxyError
from unique_search_proxy.web.core.registry import get_crawler
from unique_search_proxy.web.monitoring.metrics import (
    record_crawl_error,
    record_crawl_success,
)

router = APIRouter(tags=["crawl"])
_LOGGER = logging.getLogger(__name__)


@router.post("/crawl", response_model=CrawlResponse)
async def crawl(request: Request, body: CrawlRequest) -> CrawlResponse:
    crawler_id = body.config.crawler
    started = time.perf_counter()

    try:
        crawler_cls = get_crawler(crawler_id)
        _ = get_http_client_pool(request.app)

        crawler = crawler_cls(body.config)
        await crawler.crawl(body.urls)
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
    return CrawlResponse(crawler=crawler_id, results=[])
