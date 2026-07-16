from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, Body, Request
from unique_search_proxy_core.crawlers.config_types import CrawlRequest
from unique_search_proxy_core.errors import (
    ProxyError,
    UpstreamTimeoutError,
    attach_request_context,
)
from unique_search_proxy_core.schema import CrawlResponse, ProxyErrorCode

from unique_search_proxy_client.web.api.v1.openapi_examples import (
    CRAWL_OPENAPI_EXAMPLES,
)
from unique_search_proxy_client.web.core.client import get_http_client_pool
from unique_search_proxy_client.web.core.crawlers.factory import get_crawler_service
from unique_search_proxy_client.web.core.crawlers.pinned_egress import (
    PinnedEgressCrawler,
)
from unique_search_proxy_client.web.core.url_safety.gate import (
    apply_url_safety_gate,
    merge_crawl_results,
)
from unique_search_proxy_client.web.monitoring.metrics import (
    record_crawl_error,
    record_crawl_success,
)

router = APIRouter(tags=["crawl"])
_LOGGER = logging.getLogger(__name__)


def _crawl_request_context(exc: ProxyError, *, crawler_id: str) -> ProxyError:
    return attach_request_context(
        exc,
        request="crawl",
        provider=crawler_id,
    )


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
    _LOGGER.info(
        "crawl start crawler=%s urls=%d timeout=%ss",
        crawler_id,
        len(body.urls),
        timeout,
    )
    _LOGGER.debug("crawl urls=%r", body.urls)

    try:
        async with asyncio.timeout(timeout):
            gate = await apply_url_safety_gate(body.urls)
            if not gate.allowed_targets:
                duration = time.perf_counter() - started
                record_crawl_success(
                    crawler_id,
                    len(body.urls),
                    duration,
                )
                _LOGGER.info(
                    "crawl success crawler=%s urls=%d blocked=%d results=0 duration=%.0fms",
                    crawler_id,
                    len(body.urls),
                    len(gate.blocked_by_index),
                    duration * 1000,
                )
                return CrawlResponse(
                    crawler=crawler_id,
                    results=merge_crawl_results(
                        body.urls,
                        blocked_by_index=gate.blocked_by_index,
                        crawler_results=[],
                    ),
                )

            crawl_body = body.model_copy(
                update={
                    "urls": [target.display_url for target in gate.allowed_targets],
                },
            )

            pool = get_http_client_pool(request.app)
            crawler = get_crawler_service(crawler_id, http_client=pool.client)
            if isinstance(crawler, PinnedEgressCrawler):
                crawler_results = await crawler.crawl_pinned(
                    crawl_body,
                    gate.allowed_targets,
                )
            else:
                crawler_results = await crawler.crawl(crawl_body)
    except TimeoutError as exc:
        record_crawl_error(
            crawler_id,
            ProxyErrorCode.UPSTREAM_TIMEOUT.value,
            time.perf_counter() - started,
        )
        _LOGGER.warning(
            "crawl timeout crawler=%s timeout=%ss duration=%.0fms",
            crawler_id,
            timeout,
            (time.perf_counter() - started) * 1000,
        )
        raise _crawl_request_context(
            UpstreamTimeoutError(
                f"Crawler '{crawler_id}' timed out after {timeout}s",
            ),
            crawler_id=crawler_id,
        ) from exc
    except ProxyError as exc:
        _LOGGER.warning(
            "crawl failed crawler=%s code=%s duration=%.0fms",
            crawler_id,
            exc.code.value if hasattr(exc.code, "value") else exc.code,
            (time.perf_counter() - started) * 1000,
        )
        raise _crawl_request_context(exc, crawler_id=crawler_id) from exc
    except Exception:
        record_crawl_error(
            crawler_id,
            "INTERNAL_ERROR",
            time.perf_counter() - started,
        )
        _LOGGER.exception(
            "crawl error crawler=%s duration=%.0fms",
            crawler_id,
            (time.perf_counter() - started) * 1000,
        )
        raise

    duration = time.perf_counter() - started
    record_crawl_success(crawler_id, len(body.urls), duration)
    merged_results = merge_crawl_results(
        body.urls,
        blocked_by_index=gate.blocked_by_index,
        crawler_results=crawler_results,
    )
    _LOGGER.info(
        "crawl success crawler=%s urls=%d blocked=%d results=%d duration=%.0fms",
        crawler_id,
        len(body.urls),
        len(gate.blocked_by_index),
        len(merged_results),
        duration * 1000,
    )
    return CrawlResponse(
        crawler=crawler_id,
        results=merged_results,
    )
