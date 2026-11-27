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
    def test_build_body__reads_20_pdf_pages__by_default(self) -> None:
        """
        Purpose: Verify the reader caps PDFs at 20 pages unless told otherwise.
        Why this matters: Firecrawl bills every PDF page and the tool cuts page
            text at 10,000 tokens by default, so a whole 300-page report would
            cost 300 credits for text that is then thrown away.
        Setup summary: Build single and batch bodies with defaults; assert the
            20-page parser in both.
        """
        request = _firecrawl_request()
        expected = [{"type": "pdf", "maxPages": 20}, "image"]

        assert (
            build_firecrawl_scrape_body("https://example.com", request)["parsers"]
            == expected
        )
        assert (
            build_firecrawl_batch_scrape_body(["https://example.com"], request)[
                "parsers"
            ]
            == expected
        )

    @pytest.mark.ai
    def test_build_body__omits_parsers__when_pdfs_are_unlimited(self) -> None:
        """
        Purpose: Verify "No limit" with the default PDF mode sends no parsers.
        Why this matters: An admin who wants whole documents must get
            Firecrawl's own parser defaults, not a leftover cap.
        Setup summary: Build a body with no PDF limit; assert no `parsers`.
        """
        body = build_firecrawl_scrape_body(
            "https://example.com", _firecrawl_request(maxPdfPages=None)
        )

        assert "parsers" not in body

    @pytest.mark.ai
    def test_build_body__sends_pdf_mode__with_or_without_a_page_limit(self) -> None:
        """
        Purpose: Verify the PDF reading mode reaches Firecrawl on its own and
            together with the page limit.
        Why this matters: `fast` skips OCR and `ocr` forces it; a mode that is
            dropped when no limit is set would silently read PDFs the slow way.
        Setup summary: Build bodies with a mode and no limit, then with both;
            assert the parser object.
        """
        mode_only = build_firecrawl_scrape_body(
            "https://example.com",
            _firecrawl_request(maxPdfPages=None, pdfMode="fast"),
        )
        both = build_firecrawl_scrape_body(
            "https://example.com", _firecrawl_request(maxPdfPages=5, pdfMode="ocr")
        )

        assert mode_only["parsers"] == [{"type": "pdf", "mode": "fast"}, "image"]
        assert both["parsers"] == [
            {"type": "pdf", "mode": "ocr", "maxPages": 5},
            "image",
        ]

    @pytest.mark.ai
    def test_build_body__sends_optional_scrape_settings__only_when_changed(
        self,
    ) -> None:
        """
        Purpose: Verify cache storage, TLS and location are sent only when an
            admin changed them, under Firecrawl's field names.
        Why this matters: A default read must keep the body it always had, and
            Firecrawl ignores misnamed fields without an error.
        Setup summary: Build a default body and one with every option changed;
            assert the fields are absent, then present.
        """
        default = build_firecrawl_scrape_body(
            "https://example.com", _firecrawl_request()
        )
        changed = build_firecrawl_scrape_body(
            "https://example.com",
            _firecrawl_request(
                storeInCache=False,
                skipTlsVerification=True,
                country="CH",
                languages=["de-CH", "en"],
            ),
        )

        for field in ("storeInCache", "skipTlsVerification", "location"):
            assert field not in default
        assert changed["storeInCache"] is False
        assert changed["skipTlsVerification"] is True
        assert changed["location"] == {"country": "CH", "languages": ["de-CH", "en"]}

    @pytest.mark.ai
    def test_build_body__caps_pdf_pages__and_keeps_image_parser(self) -> None:
        """
        Purpose: Verify the PDF limit reaches Firecrawl without dropping images.
        Why this matters: A `parsers` list turns off every parser it does not
            name, so leaving out `image` would silently stop image reading.
        Setup summary: Build single and batch bodies with 10 pages; assert the
            parsers list in both.
        """
        request = _firecrawl_request(maxPdfPages=10)
        expected = [{"type": "pdf", "maxPages": 10}, "image"]

        assert (
            build_firecrawl_scrape_body("https://example.com", request)["parsers"]
            == expected
        )
        assert (
            build_firecrawl_batch_scrape_body(["https://example.com"], request)[
                "parsers"
            ]
            == expected
        )

    @pytest.mark.ai
    def test_build_body__accepts_ten_minute_old_cache__by_default(self) -> None:
        """
        Purpose: Verify the reader accepts cached pages up to ten minutes old
            by default, and Firecrawl's own two days when the admin picks that.
        Why this matters: Popular pages such as price and news pages are the
            ones most likely cached, and the model cannot see a page's age, so
            two days would pass stale figures as current. Always reading live
            costs 5 to 10 seconds per page and fails more often.
        Setup summary: Build a default body and one with no cache age; assert
            ten minutes in milliseconds, then no `maxAge`.
        """
        default = build_firecrawl_scrape_body(
            "https://example.com", _firecrawl_request()
        )
        firecrawl_default = build_firecrawl_scrape_body(
            "https://example.com", _firecrawl_request(maxCacheAgeSeconds=None)
        )

        assert default["maxAge"] == 600_000
        assert "maxAge" not in firecrawl_default

    @pytest.mark.ai
    def test_build_body__converts_cache_age_seconds__to_milliseconds(self) -> None:
        """
        Purpose: Verify the cache age in seconds is sent in milliseconds.
        Why this matters: Sent unconverted, 30 seconds would become 30
            milliseconds and every read would bypass the cache.
        Setup summary: Build a body with 30 seconds; assert 30000.
        """
        body = build_firecrawl_scrape_body(
            "https://example.com", _firecrawl_request(maxCacheAgeSeconds=30)
        )

        assert body["maxAge"] == 30_000

    @pytest.mark.ai
    def test_build_body__keeps_legacy_max_age__when_seconds_unset(self) -> None:
        """
        Purpose: Verify stored configs with the millisecond `maxAge` still work.
        Why this matters: Spaces saved before the seconds field existed must
            keep their cache age.
        Setup summary: Build bodies with only `maxAge`, then with both fields;
            assert the legacy value alone is kept and seconds win otherwise.
        """
        legacy = build_firecrawl_scrape_body(
            "https://example.com", _firecrawl_request(maxAge=5000)
        )
        both = build_firecrawl_scrape_body(
            "https://example.com",
            _firecrawl_request(maxAge=5000, maxCacheAgeSeconds=0),
        )

        assert legacy["maxAge"] == 5000
        assert both["maxAge"] == 0

    @pytest.mark.ai
    def test_request__rejects_cache_age__above_seven_days(self) -> None:
        """
        Purpose: Verify the cache age cannot exceed Firecrawl's seven-day cap.
        Why this matters: Firecrawl silently lowers larger values, so the admin
            would see a setting that is not applied.
        Setup summary: Parse a request one second over seven days; assert
            validation fails.
        """
        with pytest.raises(ValidationError):
            _firecrawl_request(maxCacheAgeSeconds=7 * 24 * 60 * 60 + 1)
