from __future__ import annotations

from typing import Any

from unique_search_proxy_core.crawlers.tavily.schema import TavilyCrawlRequest


def build_tavily_extract_body(
    urls: list[str],
    request: TavilyCrawlRequest,  # type: ignore[valid-type]
) -> dict[str, Any]:
    """Build Tavily Extract API JSON body for one batch (max 20 URLs)."""
    extract_timeout = min(max(request.timeout, 1), 60)
    body: dict[str, Any] = {
        "urls": urls,
        "format": request.format,
        "include_images": request.include_images,
        "include_favicon": request.include_favicon,
        "extract_depth": request.extract_depth,
        "timeout": extract_timeout,
        "include_usage": request.include_usage,
    }
    if request.query is not None:
        body["query"] = request.query
    if request.chunks_per_source is not None:
        body["chunks_per_source"] = request.chunks_per_source
    return body
