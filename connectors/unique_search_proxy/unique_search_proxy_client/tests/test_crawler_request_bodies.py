from __future__ import annotations

import pytest
from pydantic import ValidationError
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.config_types import parse_crawl_request
from unique_search_proxy_core.crawlers.tavily.schema import TavilyCrawlRequest

from unique_search_proxy_client.web.core.crawlers.firecrawl.request_body import (
    build_firecrawl_batch_scrape_body,
)
from unique_search_proxy_client.web.core.crawlers.jina.request_body import (
    build_jina_reader_body,
)
from unique_search_proxy_client.web.core.crawlers.tavily.request_body import (
    build_tavily_extract_body,
)


class TestTavilyRequestBody:
    @pytest.mark.ai
    def test_maps_extract_options(self) -> None:
        request = parse_crawl_request(
            {
                "urls": ["https://example.com"],
                "crawler": CrawlerType.TAVILY.value,
                "extractDepth": "basic",
                "format": "text",
                "query": "pricing",
                "chunksPerSource": 3,
                "includeImages": True,
                "includeFavicon": True,
                "includeUsage": True,
                "timeout": 45,
            },
        )
        assert isinstance(request, TavilyCrawlRequest)
        body = build_tavily_extract_body(["https://example.com"], request)
        assert body == {
            "urls": ["https://example.com"],
            "format": "text",
            "include_images": True,
            "include_favicon": True,
            "extract_depth": "basic",
            "timeout": 45,
            "include_usage": True,
            "query": "pricing",
            "chunks_per_source": 3,
        }

    @pytest.mark.ai
    def test_chunks_per_source_requires_query(self) -> None:
        with pytest.raises(ValidationError):
            parse_crawl_request(
                {
                    "urls": ["https://example.com"],
                    "crawler": CrawlerType.TAVILY.value,
                    "chunksPerSource": 2,
                },
            )


class TestJinaRequestBody:
    @pytest.mark.ai
    def test_maps_reader_options(self) -> None:
        request = parse_crawl_request(
            {
                "urls": ["https://example.com"],
                "crawler": CrawlerType.JINA.value,
                "returnFormat": "html",
                "engine": "direct",
                "pageTimeout": 20,
                "noCache": True,
                "targetSelector": ["article"],
                "waitForSelector": [".loaded"],
                "removeSelector": ["nav"],
                "withGeneratedAlt": True,
                "locale": "de-DE",
            },
        )
        body = build_jina_reader_body("https://example.com", request)
        assert body["url"] == "https://example.com"
        assert body["respondWith"] == "html"
        assert body["engine"] == "direct"
        assert body["timeout"] == 20
        assert body["noCache"] is True
        assert body["targetSelector"] == ["article"]
        assert body["waitForSelector"] == [".loaded"]
        assert body["removeSelector"] == ["nav"]
        assert body["withGeneratedAlt"] is True
        assert body["locale"] == "de-DE"
        assert body["doNotTrack"] is True


class TestFirecrawlRequestBody:
    @pytest.mark.ai
    def test_maps_batch_scrape_options(self) -> None:
        request = parse_crawl_request(
            {
                "urls": ["https://example.com"],
                "crawler": CrawlerType.FIRECRAWL.value,
                "onlyMainContent": False,
                "onlyCleanContent": True,
                "maxConcurrency": 5,
                "ignoreInvalidUrls": False,
                "waitFor": 500,
                "mobile": True,
                "blockAds": False,
                "removeBase64Images": False,
                "proxy": "enhanced",
                "includeTags": ["article"],
                "excludeTags": ["nav"],
                "scrapeHeaders": {"Cookie": "session=abc"},
                "maxAge": 3600000,
                "timeout": 90,
            },
        )
        body = build_firecrawl_batch_scrape_body(["https://example.com"], request)
        assert body["urls"] == ["https://example.com"]
        assert body["formats"] == [{"type": "markdown"}]
        assert body["timeout"] == 90_000
        assert body["onlyMainContent"] is False
        assert body["onlyCleanContent"] is True
        assert body["maxConcurrency"] == 5
        assert body["ignoreInvalidURLs"] is False
        assert body["waitFor"] == 500
        assert body["mobile"] is True
        assert body["blockAds"] is False
        assert body["removeBase64Images"] is False
        assert body["proxy"] == "enhanced"
        assert body["includeTags"] == ["article"]
        assert body["excludeTags"] == ["nav"]
        assert body["headers"] == {"Cookie": "session=abc"}
        assert body["maxAge"] == 3_600_000
