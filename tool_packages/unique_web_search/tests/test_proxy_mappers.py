import pytest
from unique_search_proxy_sdk._generated.models.crawl_response import CrawlResponse
from unique_search_proxy_sdk._generated.models.crawl_url_result import CrawlUrlResult

from unique_web_search.services.proxy.mappers import map_crawl_response


@pytest.mark.ai
def test_map_crawl_response__uses_positional_mapping__when_result_urls_differ() -> None:
    """Purpose: Verify crawl markdown is aligned by request order, not exact URL strings.

    Why this matters: The proxy may return canonical URLs after redirects while preserving
    per-request result order; exact URL lookup would drop successful crawls.
    Setup summary: One requested URL with a different canonical URL in the response body.
    """
    requested_urls = ["http://example.com/page"]
    response = CrawlResponse(
        crawler="basic",
        results=[
            CrawlUrlResult(
                url="https://www.example.com/page",
                content="# Hello",
            )
        ],
    )

    assert map_crawl_response(response, requested_urls) == [
        "URL: https://www.example.com/page\n\n# Hello"
    ]


@pytest.mark.ai
def test_map_crawl_response__includes_url_in_error__when_crawl_fails() -> None:
    """Purpose: Verify per-URL errors carry the proxy-reported URL as context.

    Why this matters: Canonical response URLs may differ from the request string.
    Setup summary: Crawl result with a PerUrlError and a distinct result URL.
    """
    from unique_search_proxy_sdk._generated.models.per_url_error import PerUrlError

    requested_urls = ["http://example.com/page"]
    response = CrawlResponse(
        crawler="basic",
        results=[
            CrawlUrlResult(
                url="https://www.example.com/page",
                error=PerUrlError(
                    code="UPSTREAM_HTTP_ERROR",
                    message="HTTP 403 while fetching URL",
                ),
            )
        ],
    )

    assert map_crawl_response(response, requested_urls) == [
        "URL: https://www.example.com/page\n\nError: HTTP 403 while fetching URL"
    ]
