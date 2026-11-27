from __future__ import annotations

import pytest
from pydantic import ValidationError
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.config_types import parse_crawl_request
from unique_search_proxy_core.crawlers.tavily.schema import TavilyCrawlRequest

from unique_search_proxy_client.web.core.crawlers.firecrawl.request_body import (
    build_firecrawl_batch_scrape_body,
    build_firecrawl_scrape_body,
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
    def test_maps_scrape_options(self) -> None:
        request = parse_crawl_request(
            {
                "urls": ["https://example.com"],
                "crawler": CrawlerType.FIRECRAWL.value,
                "onlyMainContent": False,
                "waitFor": 500,
                "proxy": "enhanced",
                "timeout": 90,
            },
        )
        body = build_firecrawl_scrape_body("https://example.com", request)
        assert body["url"] == "https://example.com"
        assert body["formats"] == [{"type": "markdown"}]
        assert body["timeout"] == 90_000
        assert body["onlyMainContent"] is False
        assert body["waitFor"] == 500
        assert body["proxy"] == "enhanced"
        assert "urls" not in body
        assert "maxConcurrency" not in body

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


def _firecrawl_request(**fields: object) -> object:
    return parse_crawl_request(
        {
            "urls": ["https://example.com"],
            "crawler": CrawlerType.FIRECRAWL.value,
            **fields,
        },
    )


class TestFirecrawlCacheAndRetention:
    @pytest.mark.ai
    def test_build_body__omits_zero_data_retention__by_default(self) -> None:
        request = _firecrawl_request()

        assert "zeroDataRetention" not in build_firecrawl_scrape_body(
            "https://example.com", request
        )
        assert "zeroDataRetention" not in build_firecrawl_batch_scrape_body(
            ["https://example.com"], request
        )

    @pytest.mark.ai
    def test_build_body__sends_zero_data_retention__when_enabled(self) -> None:
        request = _firecrawl_request()

        single = build_firecrawl_scrape_body(
            "https://example.com", request, zero_data_retention=True
        )
        batch = build_firecrawl_batch_scrape_body(
            ["https://example.com"], request, zero_data_retention=True
        )

        assert single["zeroDataRetention"] is True
        assert batch["zeroDataRetention"] is True

    @pytest.mark.ai
    def test_build_body__caps_cache_age_and_pdf_pages__by_default(self) -> None:
        request = _firecrawl_request()
        single = build_firecrawl_scrape_body("https://example.com", request)
        batch = build_firecrawl_batch_scrape_body(["https://example.com"], request)

        for body in (single, batch):
            assert body["maxAge"] == 600_000
            assert body["parsers"] == [{"type": "pdf", "maxPages": 20}, "image"]

    @pytest.mark.ai
    def test_request__reads_null_cache_age_and_pdf_cap__as_the_defaults(self) -> None:
        request = _firecrawl_request(maxAge=None, maxPdfPages=None)

        assert request.max_age == 600_000
        assert request.max_pdf_pages == 20

    @pytest.mark.ai
    def test_build_body__sends_cache_storage_and_location__only_when_changed(
        self,
    ) -> None:
        default = build_firecrawl_scrape_body(
            "https://example.com", _firecrawl_request()
        )
        changed = build_firecrawl_scrape_body(
            "https://example.com",
            _firecrawl_request(
                storeInCache=False, country="CH", languages=["de-CH", "en"]
            ),
        )

        assert "storeInCache" not in default
        assert "location" not in default
        assert changed["storeInCache"] is False
        assert changed["location"] == {"country": "CH", "languages": ["de-CH", "en"]}
