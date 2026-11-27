from __future__ import annotations

import pytest
from pydantic import ValidationError

from unique_search_proxy_client.web.settings.providers.firecrawl import (
    _FirecrawlCredentials,
)
from unique_search_proxy_client.web.settings.providers.jina import _JinaCredentials
from unique_search_proxy_client.web.settings.providers.tavily import _TavilyCredentials


class TestCrawlerProviderEndpoints:
    """Endpoint URLs and zero data retention modes built by the crawler provider credentials."""

    @pytest.mark.ai
    def test_tavily_endpoints(self) -> None:
        credentials = _TavilyCredentials(
            api_key="key",
            api_endpoint="https://api.tavily.com",
        )
        assert credentials.extract_endpoint == "https://api.tavily.com/extract"
        assert credentials.search_endpoint == "https://api.tavily.com/search"

    @pytest.mark.ai
    def test_tavily_default_base(self) -> None:
        credentials = _TavilyCredentials(api_key="key")
        assert credentials.extract_endpoint == "https://api.tavily.com/extract"
        assert credentials.search_endpoint == "https://api.tavily.com/search"

    @pytest.mark.ai
    def test_jina_global_endpoints(self) -> None:
        credentials = _JinaCredentials(api_key="key", deployment="global")
        assert credentials.reader_endpoint == "https://r.jina.ai/"
        assert credentials.search_endpoint == "https://s.jina.ai/"

    @pytest.mark.ai
    def test_jina_eu_beta_endpoints(self) -> None:
        credentials = _JinaCredentials(api_key="key", deployment="eu-beta")
        assert credentials.reader_endpoint == "https://eu-r-beta.jina.ai/"
        assert credentials.search_endpoint == "https://eu-s-beta.jina.ai/"

    @pytest.mark.ai
    def test_firecrawl_v2_endpoints(self) -> None:
        credentials = _FirecrawlCredentials(
            api_key="key",
            api_endpoint="https://api.firecrawl.dev",
            api_version="v2",
        )
        assert (
            credentials.batch_scrape_endpoint
            == "https://api.firecrawl.dev/v2/batch/scrape"
        )
        assert credentials.scrape_endpoint == "https://api.firecrawl.dev/v2/scrape"
        assert credentials.search_endpoint == "https://api.firecrawl.dev/v2/search"

    @pytest.mark.ai
    def test_firecrawl_default_base_and_version(self) -> None:
        credentials = _FirecrawlCredentials(api_key="key")
        assert credentials.batch_scrape_endpoint == (
            "https://api.firecrawl.dev/v2/batch/scrape"
        )
        assert credentials.scrape_endpoint == "https://api.firecrawl.dev/v2/scrape"

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("zero_data_retention", "expected"),
        [("none", []), ("anon", ["anon"]), ("zdr", ["zdr"])],
        ids=["none", "anon", "zdr"],
    )
    def test_firecrawl_search_enterprise_modes__follow_setting(
        self,
        zero_data_retention: str,
        expected: list[str],
    ) -> None:
        """
        Purpose: Verify the zero data retention setting maps to Firecrawl's
            `enterprise` list.
        Why this matters: `none` must send nothing, because Firecrawl rejects
            the field for accounts without zero data retention.
        Setup summary: Build credentials per setting; assert the modes list.
        """
        credentials = _FirecrawlCredentials(
            api_key="key", zero_data_retention=zero_data_retention
        )

        assert credentials.search_enterprise_modes() == expected

    @pytest.mark.ai
    def test_firecrawl_zero_data_retention__defaults_to_none(self) -> None:
        """
        Purpose: Verify zero data retention is off unless an operator sets it.
        Why this matters: Deployments that already use the Firecrawl crawler
            must keep working after the upgrade without a new setting.
        Setup summary: Build credentials with only a key; assert the default.
        """
        credentials = _FirecrawlCredentials(api_key="key")

        assert credentials.zero_data_retention == "none"
        assert credentials.search_enterprise_modes() == []

    @pytest.mark.ai
    def test_firecrawl_zero_data_retention__rejects_unknown_mode(self) -> None:
        """
        Purpose: Verify an unknown zero data retention mode fails at startup.
        Why this matters: A typo such as `ZDR ` must not silently fall back to
            normal retention.
        Setup summary: Build credentials with an unknown mode; assert the error.
        """
        with pytest.raises(ValidationError):
            _FirecrawlCredentials(api_key="key", zero_data_retention="strict")

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("zero_data_retention", "expected"),
        [("none", False), ("anon", True), ("zdr", True)],
        ids=["none", "anon", "zdr"],
    )
    def test_firecrawl_scrape_zero_data_retention__follows_setting(
        self,
        zero_data_retention: str,
        expected: bool,
    ) -> None:
        """
        Purpose: Verify page reads use zero data retention whenever searches do.
        Why this matters: Page reads have no anonymized mode; an operator who
            asked for `anon` must not get page content retained, and `none`
            must keep the request unchanged for existing deployments.
        Setup summary: Build credentials per setting; assert the page-read flag.
        """
        credentials = _FirecrawlCredentials(
            api_key="key", zero_data_retention=zero_data_retention
        )

        assert credentials.scrape_zero_data_retention() is expected

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("deployed", "requested", "expected"),
        [
            ("none", "deployment", []),
            ("none", "anon", ["anon"]),
            ("none", "zdr", ["zdr"]),
            ("anon", "deployment", ["anon"]),
            ("anon", "zdr", ["zdr"]),
            ("zdr", "deployment", ["zdr"]),
            ("zdr", "anon", ["zdr"]),
        ],
    )
    def test_firecrawl_search_enterprise_modes__take_the_stricter_mode(
        self,
        deployed: str,
        requested: str,
        expected: list[str],
    ) -> None:
        """
        Purpose: Verify a search uses the stricter of the deployed mode and the
            mode its configuration asks for.
        Why this matters: A space may need end-to-end zero data retention on a
            deployment that only anonymizes, but no configuration may weaken
            what the operator set for the whole deployment.
        Setup summary: Combine each deployed mode with a requested one; assert
            the `enterprise` list.
        """
        credentials = _FirecrawlCredentials(api_key="key", zero_data_retention=deployed)

        assert credentials.search_enterprise_modes(requested) == expected

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("deployed", "requested", "expected"),
        [
            ("none", False, False),
            ("none", True, True),
            ("anon", False, True),
            ("zdr", False, True),
            ("zdr", True, True),
        ],
    )
    def test_firecrawl_scrape_zero_data_retention__is_on_when_either_asks(
        self,
        deployed: str,
        requested: bool,
        expected: bool,
    ) -> None:
        """
        Purpose: Verify a page read uses zero data retention when the
            deployment or the crawler configuration asks for it.
        Why this matters: A configuration that leaves the switch off must not
            turn off what the operator set for the whole deployment.
        Setup summary: Combine each deployed mode with the request switch;
            assert the page-read flag.
        """
        credentials = _FirecrawlCredentials(api_key="key", zero_data_retention=deployed)

        assert credentials.scrape_zero_data_retention(requested) is expected
