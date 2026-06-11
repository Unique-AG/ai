import pytest
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.config_types import CrawlRequest
from unique_search_proxy_core.schema import (
    CrawlResponse,
    SearchResponse,
    WebSearchResult,
)
from unique_search_proxy_core.search_engines.config_types import SearchRequest
from unique_search_proxy_core.search_engines.google.schema import GoogleRequest


class TestV1SearchSchemas:
    @pytest.mark.ai
    def test_search_request_camel_case(self) -> None:
        req = SearchRequest.model_validate(
            {
                "engine": "google",
                "query": "test",
                "fetchSize": 10,
                "timeout": 60,
            },
        )
        assert isinstance(req, GoogleRequest)
        assert req.timeout == 60

    @pytest.mark.ai
    def test_search_response(self) -> None:
        resp = SearchResponse(
            engine="google",
            query="test",
            raw={"items": []},
            curated=[WebSearchResult(url="u", title="t", snippet="s")],
        )
        assert resp.engine == "google"
        assert len(resp.curated) == 1


class TestV1CrawlSchemas:
    @pytest.mark.ai
    def test_crawl_request(self) -> None:
        req = CrawlRequest.model_validate(
            {
                "urls": ["https://example.com"],
                "crawler": CrawlerType.BASIC.value,
            },
        )
        assert req.urls == ["https://example.com"]

    @pytest.mark.ai
    def test_crawl_response_empty_results(self) -> None:
        resp = CrawlResponse(crawler=CrawlerType.BASIC.value, results=[])
        assert resp.crawler == CrawlerType.BASIC
