from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_search_proxy_core.search_engines import SearchEngineType
from unique_search_proxy_core.search_engines.firecrawl.schema import (
    ExposableCountry,
    ExposableTimeFilter,
)

from unique_web_search.services.search_engine import get_search_engine_service
from unique_web_search.services.search_engine.firecrawl import (
    FirecrawlSearch,
    FirecrawlSearchConfig,
)
from unique_web_search.services.search_engine.schema import WebSearchResult

_BASE = "unique_web_search.services.search_engine.base"


@contextmanager
def _proxy_search(mock_search: AsyncMock) -> Iterator[Mock]:
    """Route searches to a mocked Search Proxy client and yield its opener."""
    with (
        patch(f"{_BASE}.search_proxy_client_enabled", True),
        patch(f"{_BASE}.open_search_proxy_client") as mock_open_client,
    ):
        mock_client = AsyncMock()
        mock_client.search.search = mock_search
        mock_open_client.return_value.__aenter__.return_value = mock_client
        yield mock_open_client


class TestFirecrawlSearchConfig:
    @pytest.mark.ai
    def test_config__reads_no_result_pages__by_default(self) -> None:
        """
        Purpose: Verify by default a search returns previews only: neither the
            Web Page Reader nor Firecrawl reads the result pages.
        Why this matters: The default decides who connects to the result
            websites and what a search costs. Reading every result costs a
            credit per page (two with zero data retention) on every search,
            while in search mode V3 the model reads only the pages it needs.
        Setup summary: Build a default config; assert both switches and the
            preview limit.
        """
        config = FirecrawlSearchConfig()

        assert config.engine == SearchEngineType.FIRECRAWL
        assert config.requires_scraping is False
        assert config.scrape_results is False
        assert config.repeated_preview_max_chars == 500
        assert FirecrawlSearch(config).requires_scraping is False

    @pytest.mark.ai
    def test_config__lists_page_reading_settings__under_requires_scraping(
        self,
    ) -> None:
        """
        Purpose: Verify the admin form shows 'Requires scraping' directly above
            the settings that only apply when it is on, after the search options.
        Why this matters: Field order is the form order. Settings that depend on
            a switch shown elsewhere look as if they always applied.
        Setup summary: Read the field order of the config; assert the last six
            fields and that the same order reaches the JSON schema.
        """
        expected_tail = [
            "requires_scraping",
            "scrape_results",
            "only_main_content",
            "max_cache_age_seconds",
            "max_pdf_pages",
            "repeated_preview_max_chars",
        ]
        schema = FirecrawlSearchConfig.model_json_schema(by_alias=True)

        assert list(FirecrawlSearchConfig.model_fields)[-6:] == expected_tail
        assert list(schema["properties"])[-6:] == [
            "requiresScraping",
            "scrapeResults",
            "onlyMainContent",
            "maxCacheAgeSeconds",
            "maxPdfPages",
            "repeatedPreviewMaxChars",
        ]

    @pytest.mark.ai
    def test_config__names_the_scraping_switch__like_other_engines(self) -> None:
        """
        Purpose: Verify the page-reading switch has the same name, type and
            null handling as on Brave and Google.
        Why this matters: The admin form carries the value over when the engine
            is switched and stores null in between; a different name or type
            would lose the admin's choice or fail the space config.
        Setup summary: Read the JSON schema; load a config with null; assert both.
        """
        schema = FirecrawlSearchConfig.model_json_schema(by_alias=True)
        config = FirecrawlSearchConfig.model_validate(
            {"engine": "firecrawl", "requiresScraping": None}
        )

        assert schema["properties"]["requiresScraping"]["type"] == ["boolean", "null"]
        assert schema["properties"]["requiresScraping"]["title"] == "Requires scraping"
        assert config.requires_scraping is False


class TestFirecrawlSearchInit:
    @pytest.mark.ai
    def test_service__is_resolved_from_registry__for_firecrawl_config(self) -> None:
        """
        Purpose: Verify a Firecrawl config resolves to the Firecrawl engine.
        Why this matters: The tool picks the engine from the space config; an
            unregistered engine fails every search in that space.
        Setup summary: Resolve the service for a default config; assert its type.
        """
        service = get_search_engine_service(FirecrawlSearchConfig(), Mock())

        assert isinstance(service, FirecrawlSearch)

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("requires_scraping", "scrape_results", "expected"),
        [
            (True, False, True),
            (True, True, False),
            (False, False, False),
            (False, True, False),
        ],
        ids=["reader", "inside-search", "off", "off-wins"],
    )
    def test_requires_scraping__runs_web_page_reader__unless_firecrawl_read_pages(
        self,
        requires_scraping: bool,
        scrape_results: bool,
        expected: bool,
    ) -> None:
        """
        Purpose: Verify the Web Page Reader runs when scraping is required and
            Firecrawl did not already read the pages inside the search.
        Why this matters: Crawling pages Firecrawl already read fetches each
            page twice and pays twice; crawling with scraping off contacts
            websites the admin did not want read.
        Setup summary: Build the engine for each switch combination; assert its
            crawl decision.
        """
        search = FirecrawlSearch(
            FirecrawlSearchConfig(
                requires_scraping=requires_scraping, scrape_results=scrape_results
            )
        )

        assert search.requires_scraping is expected

    @pytest.mark.ai
    def test_is_configured__follows_search_proxy__without_local_credentials(
        self,
    ) -> None:
        """
        Purpose: Verify Firecrawl search counts as configured only with the
            Search Proxy.
        Why this matters: The engine has no direct mode; reporting it as
            configured without the proxy would offer an engine that cannot run.
        Setup summary: Build the engine with the proxy on and off; assert the flag.
        """
        module = "unique_web_search.services.search_engine.firecrawl"
        with patch(f"{module}.search_proxy_client_enabled", True):
            enabled = FirecrawlSearch(FirecrawlSearchConfig()).is_configured
        with patch(f"{module}.search_proxy_client_enabled", False):
            disabled = FirecrawlSearch(FirecrawlSearchConfig()).is_configured

        assert enabled is True
        assert disabled is False


class TestFirecrawlSearch:
    @pytest.mark.ai
    async def test_legacy_search__raises_not_implemented(self) -> None:
        """
        Purpose: Verify Firecrawl search has no direct (non-proxy) mode.
        Why this matters: A silent fallback would call Firecrawl from the
            assistant with no key and no zero data retention setting.
        Setup summary: Call the legacy path; assert NotImplementedError.
        """
        search = FirecrawlSearch(FirecrawlSearchConfig())

        with pytest.raises(
            NotImplementedError,
            match="Firecrawl search is not supported in the legacy mode",
        ):
            await search._legacy_search("query", params=None)

    @pytest.mark.ai
    async def test_search__sends_admin_settings_to_proxy__and_keeps_page_content(
        self,
    ) -> None:
        """
        Purpose: Verify the admin's settings reach the Search Proxy and the
            scraped page content is returned.
        Why this matters: Dropped settings change which sources are searched;
            dropped content means the model only sees snippets.
        Setup summary: Search with a configured engine against a mocked proxy;
            assert the call kwargs and the mapped result.
        """
        config = FirecrawlSearchConfig(
            fetch_size=3,
            sources="web_and_news",
            requires_scraping=True,
            scrape_results=True,
            exclude_domains=["blocked.com"],
            time_filter=ExposableTimeFilter(expose=False, value="qdr:w"),
            country=ExposableCountry(expose=False, value="CH"),
        )
        response = Mock()
        response.curated = [
            Mock(
                url="https://example.com/page",
                title="Hit",
                snippet="Details",
                content="# Page",
            )
        ]
        mock_search = AsyncMock(return_value=response)

        with _proxy_search(mock_search):
            results = await FirecrawlSearch(config).search("test query")

        call_kwargs = mock_search.await_args.kwargs
        assert call_kwargs["query"] == "test query"
        assert call_kwargs["engine"] == "firecrawl"
        assert call_kwargs["fetch_size"] == 3
        assert call_kwargs["sources"] == "web_and_news"
        assert call_kwargs["exclude_domains"] == ["blocked.com"]
        assert call_kwargs["time_filter"] == "qdr:w"
        assert call_kwargs["country"] == "CH"
        assert call_kwargs["scrape_results"] is True
        assert "requires_scraping" not in call_kwargs
        assert "repeated_preview_max_chars" not in call_kwargs
        assert results == [
            WebSearchResult(
                url="https://example.com/page",
                title="Hit",
                snippet="Details",
                content="# Page",
            )
        ]

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("requires_scraping", "scrape_results"),
        [(True, False), (False, True), (False, False)],
        ids=["reader", "scraping-off-wins", "off"],
    )
    async def test_search__asks_proxy_for_previews_only__unless_both_switches_are_on(
        self,
        requires_scraping: bool,
        scrape_results: bool,
    ) -> None:
        """
        Purpose: Verify Firecrawl reads pages inside the search only when
            scraping is required and the inside-search option is on.
        Why this matters: 'Requires scraping' is the one switch for reading
            pages, as on every other engine. With it off, a leftover
            inside-search option must not make Firecrawl read and bill every
            result page.
        Setup summary: Search with each other combination; assert the proxy is
            asked for previews only.
        """
        config = FirecrawlSearchConfig(
            requires_scraping=requires_scraping, scrape_results=scrape_results
        )
        mock_search = AsyncMock(return_value=Mock(curated=[]))

        with _proxy_search(mock_search):
            await FirecrawlSearch(config).search("test query")

        call_kwargs = mock_search.await_args.kwargs
        assert call_kwargs["engine"] == "firecrawl"
        assert call_kwargs["scrape_results"] is False

    @pytest.mark.ai
    async def test_search__returns_long_previews_whole(self) -> None:
        """
        Purpose: Verify the engine itself never cuts a preview.
        Why this matters: In search mode V3 the preview is all the model sees
            of a result, and Firecrawl's query-matched previews can hold the
            whole table the question is about.
        Setup summary: Mock a 5,000-character preview; assert it comes back whole.
        """
        long_preview = "price " * 833
        response = Mock()
        response.curated = [
            Mock(url="https://example.com", title="T", snippet=long_preview, content="")
        ]

        with _proxy_search(AsyncMock(return_value=response)):
            results = await FirecrawlSearch(FirecrawlSearchConfig()).search("q")

        assert results[0].snippet == long_preview

    @pytest.mark.ai
    async def test_search__waits_longer_than_engine_timeout__for_proxy(self) -> None:
        """
        Purpose: Verify the proxy client timeout follows the engine timeout
            instead of the 30 second default.
        Why this matters: Firecrawl can read the pages inside the search call;
            with the default the tool gives up while the search still runs.
        Setup summary: Search with a 90 second engine timeout; assert the
            timeout passed to the proxy client.
        """
        mock_search = AsyncMock(return_value=Mock(curated=[]))

        with _proxy_search(mock_search) as mock_open_client:
            await FirecrawlSearch(FirecrawlSearchConfig(timeout=90)).search("q")

        assert mock_open_client.call_args.kwargs["timeout"] == 100.0
