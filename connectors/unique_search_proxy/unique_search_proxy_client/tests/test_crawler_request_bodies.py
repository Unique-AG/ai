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
    """Parse a Firecrawl crawl request for one example URL.

    Args:
        **fields (object): Request fields, camelCase, added to the defaults.

    Returns:
        object: The parsed Firecrawl crawl request.
    """
    return parse_crawl_request(
        {
            "urls": ["https://example.com"],
            "crawler": CrawlerType.FIRECRAWL.value,
            **fields,
        },
    )


class TestFirecrawlCacheAndRetention:
    """Firecrawl scrape bodies: cache, zero data retention, proxy, PDF and location."""

    @pytest.mark.ai
    def test_build_body__omits_zero_data_retention__by_default(self) -> None:
        """
        Purpose: Verify page reads send no zero data retention field by default.
        Why this matters: Firecrawl rejects the field for accounts without zero
            data retention, so existing deployments must keep sending the same
            body after the upgrade.
        Setup summary: Build single and batch bodies with defaults; assert the
            field is absent.
        """
        request = _firecrawl_request()

        assert "zeroDataRetention" not in build_firecrawl_scrape_body(
            "https://example.com", request
        )
        assert "zeroDataRetention" not in build_firecrawl_batch_scrape_body(
            ["https://example.com"], request
        )

    @pytest.mark.ai
    def test_build_body__sends_zero_data_retention__when_enabled(self) -> None:
        """
        Purpose: Verify the zero data retention setting reaches Firecrawl.
        Why this matters: Without the field Firecrawl keeps the page content,
            which a zero data retention contract forbids.
        Setup summary: Build single and batch bodies with the flag on; assert
            `zeroDataRetention: true` in both.
        """
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
    def test_build_body__omits_proxy_mode__by_default(self) -> None:
        """
        Purpose: Verify the proxy mode is only sent when changed.
        Why this matters: `auto` is Firecrawl's own default, so a default read
            keeps the body it always had; a chosen tier must reach Firecrawl.
        Setup summary: Build bodies with the default and with `enhanced`;
            assert the field is absent, then present.
        """
        default = build_firecrawl_scrape_body(
            "https://example.com", _firecrawl_request()
        )
        enhanced = build_firecrawl_scrape_body(
            "https://example.com", _firecrawl_request(proxy="enhanced")
        )

        assert "proxy" not in default
        assert enhanced["proxy"] == "enhanced"

    @pytest.mark.ai
    def test_build_body__caps_cache_age_and_pdf_pages__by_default(self) -> None:
        """
        Purpose: Verify a default read accepts cached pages up to ten minutes
            old and reads at most 20 pages of a PDF, for one and several URLs.
        Why this matters: Firecrawl's own two-day cache passes stale prices as
            current, and it bills every PDF page while the tool cuts page text
            at 10,000 tokens, so a 300-page report would cost 300 credits for
            text that is thrown away. `image` must stay listed, because a
            `parsers` list turns off every parser it does not name.
        Setup summary: Build single and batch bodies with defaults; assert
            `maxAge` and `parsers` in both.
        """
        request = _firecrawl_request()
        single = build_firecrawl_scrape_body("https://example.com", request)
        batch = build_firecrawl_batch_scrape_body(["https://example.com"], request)

        for body in (single, batch):
            assert body["maxAge"] == 600_000
            assert body["parsers"] == [{"type": "pdf", "maxPages": 20}, "image"]

    @pytest.mark.ai
    def test_request__reads_null_cache_age_and_pdf_cap__as_the_defaults(self) -> None:
        """
        Purpose: Verify a null cache age or PDF cap loads as the default.
        Why this matters: Null values are dropped between the web search tool,
            the SDK and the proxy, so null can never mean "no limit". A null
            left in a stored config must not make the space's web search fail.
        Setup summary: Parse a request with both fields null; assert the
            defaults.
        """
        request = _firecrawl_request(maxAge=None, maxPdfPages=None)

        assert request.max_age == 600_000
        assert request.max_pdf_pages == 20

    @pytest.mark.ai
    def test_build_body__sends_firecrawl_own_limits__when_configured(self) -> None:
        """
        Purpose: Verify the old behaviour can be configured with numbers: a
            two-day cache and Firecrawl's maximum of 10,000 PDF pages.
        Why this matters: The changelog tells operators to use these values to
            get the previous reader behaviour back.
        Setup summary: Build a body with both values; assert them.
        """
        body = build_firecrawl_scrape_body(
            "https://example.com",
            _firecrawl_request(maxAge=172_800_000, maxPdfPages=10_000),
        )

        assert body["maxAge"] == 172_800_000
        assert body["parsers"] == [{"type": "pdf", "maxPages": 10_000}, "image"]

    @pytest.mark.ai
    def test_build_body__sends_cache_storage_and_location__only_when_changed(
        self,
    ) -> None:
        """
        Purpose: Verify cache storage and location are sent only when an admin
            changed them, under Firecrawl's field names.
        Why this matters: A default read must keep the body it always had, and
            Firecrawl ignores misnamed fields without an error.
        Setup summary: Build a default body and one with both options changed;
            assert the fields are absent, then present.
        """
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

    @pytest.mark.ai
    def test_request__rejects_cache_age__above_seven_days(self) -> None:
        """
        Purpose: Verify the cache age cannot exceed Firecrawl's seven-day cap.
        Why this matters: Firecrawl silently lowers larger values, so the admin
            would see a setting that is not applied.
        Setup summary: Parse a request one millisecond over seven days; assert
            validation fails.
        """
        with pytest.raises(ValidationError):
            _firecrawl_request(maxAge=7 * 24 * 60 * 60 * 1000 + 1)
