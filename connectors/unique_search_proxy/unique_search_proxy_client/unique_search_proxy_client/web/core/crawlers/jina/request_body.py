from __future__ import annotations

from typing import Any

from unique_search_proxy_core.crawlers.jina.schema import JinaCrawlRequest


def build_jina_reader_body(url: str, request: JinaCrawlRequest) -> dict[str, Any]:
    """Build Jina Reader POST JSON body for one URL."""
    page_timeout = request.page_timeout
    if page_timeout is None:
        page_timeout = min(max(request.timeout, 1), 180)

    body: dict[str, Any] = {
        "url": url,
        "respondWith": request.return_format,
        "engine": request.engine,
        "timeout": page_timeout,
        "doNotTrack": request.do_not_track,
    }

    if request.no_cache:
        body["noCache"] = True
    if request.target_selector is not None:
        body["targetSelector"] = request.target_selector
    if request.wait_for_selector is not None:
        body["waitForSelector"] = request.wait_for_selector
    if request.remove_selector is not None:
        body["removeSelector"] = request.remove_selector
    if request.with_generated_alt:
        body["withGeneratedAlt"] = True
    if request.with_links_summary:
        body["withLinksSummary"] = True
    if request.with_images_summary:
        body["withImagesSummary"] = True
    if request.with_iframe:
        body["withIframe"] = True
    if request.retain_images is not None:
        body["retainImages"] = request.retain_images
    if request.locale is not None:
        body["locale"] = request.locale
    if request.referer is not None:
        body["referer"] = request.referer
    if request.proxy_url is not None:
        body["proxyUrl"] = request.proxy_url

    return body
