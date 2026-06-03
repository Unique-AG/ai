import pytest

from unique_search_proxy.web.api.v1.schema import (
    CrawlRequest,
    CrawlResponse,
    SearchRequest,
    SearchResponse,
)
from unique_search_proxy.web.core.schema import WebSearchResult


class TestV1SearchSchemas:
    @pytest.mark.ai
    def test_search_request_camel_case(self) -> None:
        req = SearchRequest.model_validate(
            {
                "config": {"engine": "google"},
                "call": {"query": "test"},
                "includeContent": True,
                "timeout": 60,
            },
        )
        assert req.include_content is True
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
                "config": {"crawler": "basic"},
            },
        )
        assert req.urls == ["https://example.com"]

    @pytest.mark.ai
    def test_crawl_response_empty_results(self) -> None:
        resp = CrawlResponse(crawler="basic", results=[])
        assert resp.crawler == "basic"
