from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_search_proxy_core.search_engines import SearchEngineType
from unique_search_proxy_core.search_engines.firecrawl.schema import (
    ExposableCountry,
    ExposableTimeFilter,
)

from unique_web_search.services.search_engine.firecrawl import (
    FirecrawlSearch,
    FirecrawlSearchConfig,
)
from unique_web_search.services.search_engine.schema import WebSearchResult

_BASE = "unique_web_search.services.search_engine.base"


@contextmanager
def _proxy_search(mock_search: AsyncMock) -> Iterator[Mock]:
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
        config = FirecrawlSearchConfig()
        scraping = FirecrawlSearchConfig(requires_scraping=True)

        assert config.engine == SearchEngineType.FIRECRAWL
        assert config.requires_scraping is False
        assert config.repeated_preview_max_chars == 500
        assert FirecrawlSearch(config).requires_scraping is False
        assert FirecrawlSearch(scraping).requires_scraping is True

    @pytest.mark.ai
    def test_config__names_the_scraping_switch__like_other_engines(self) -> None:
        schema = FirecrawlSearchConfig.model_json_schema(by_alias=True)
        config = FirecrawlSearchConfig.model_validate(
            {"engine": "firecrawl", "requiresScraping": None}
        )

        assert schema["properties"]["requiresScraping"]["type"] == ["boolean", "null"]
        assert schema["properties"]["requiresScraping"]["title"] == "Requires scraping"
        assert config.requires_scraping is False


class TestFirecrawlSearchInit:
    @pytest.mark.ai
    def test_is_configured__follows_search_proxy__without_local_credentials(
        self,
    ) -> None:
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
        search = FirecrawlSearch(FirecrawlSearchConfig())

        with pytest.raises(
            NotImplementedError,
            match="Firecrawl search is not supported in the legacy mode",
        ):
            await search._legacy_search("query", params=None)

    @pytest.mark.ai
    async def test_search__sends_admin_settings_to_proxy__without_tool_only_fields(
        self,
    ) -> None:
        config = FirecrawlSearchConfig(
            fetch_size=3,
            sources="web_and_news",
            requires_scraping=True,
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
                content="",
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
        assert "requires_scraping" not in call_kwargs
        assert "repeated_preview_max_chars" not in call_kwargs
        assert results == [
            WebSearchResult(
                url="https://example.com/page",
                title="Hit",
                snippet="Details",
                content="",
            )
        ]
