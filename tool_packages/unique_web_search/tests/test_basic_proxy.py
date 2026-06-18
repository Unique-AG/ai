from unique_search_proxy_sdk._generated.models.crawl_response import CrawlResponse
from unique_search_proxy_sdk._generated.models.crawl_url_result import CrawlUrlResult
from unique_search_proxy_sdk._generated.models.per_url_error import PerUrlError

from unique_web_search.services.crawlers import get_crawler_service
from unique_web_search.services.crawlers.base import CrawlerType
from unique_web_search.services.crawlers.basic import BasicCrawler, BasicCrawlerConfig
from unique_web_search.services.proxy.mappers import (
    map_crawl_response,
    result_to_markdown,
)


class TestBasicCrawlerFactory:
    def test_get_basic_crawler_service(self) -> None:
        config = BasicCrawlerConfig(crawler_type=CrawlerType.BASIC)
        service = get_crawler_service(config)
        assert isinstance(service, BasicCrawler)
        assert service.config.crawler_type == CrawlerType.BASIC


class TestResultToMarkdown:
    def test_content_string(self) -> None:
        result = CrawlUrlResult(url="https://example.com", content="# Title")
        assert result_to_markdown(result) == "# Title"

    def test_per_url_error(self) -> None:
        result = CrawlUrlResult(
            url="https://example.com",
            error=PerUrlError(code="timeout", message="timed out"),
        )
        assert result_to_markdown(result) == "Error: timed out"

    def test_raw_string(self) -> None:
        result = CrawlUrlResult(
            url="https://example.com",
            raw="<html>body</html>",
        )
        assert result_to_markdown(result) == "<html>body</html>"

    def test_no_content_fallback(self) -> None:
        result = CrawlUrlResult(url="https://example.com")
        assert (
            result_to_markdown(result) == "Error: No content returned by search proxy"
        )


class TestMapCrawlResponse:
    def test_map_crawl_response__maps_all_urls_in_order(self) -> None:
        urls = ["https://example.com", "https://missing.example"]
        response = CrawlResponse(
            results=[
                CrawlUrlResult(
                    url="https://example.com",
                    content="markdown body",
                ),
                CrawlUrlResult(
                    url="https://missing.example",
                    content="missing",
                ),
            ],
            crawler="Basic",
        )

        assert map_crawl_response(response, urls) == ["markdown body", "missing"]

    def test_map_crawl_response__missing_url_gets_fallback_error(self) -> None:
        urls = ["https://example.com", "https://missing.example"]
        response = CrawlResponse(
            results=[
                CrawlUrlResult(
                    url="https://example.com",
                    content="markdown body",
                ),
                CrawlUrlResult(
                    url="https://other.example",
                    content="other body",
                ),
            ],
            crawler="Basic",
        )

        assert map_crawl_response(response, urls) == [
            "markdown body",
            "Error: URL not found in search proxy response",
        ]
