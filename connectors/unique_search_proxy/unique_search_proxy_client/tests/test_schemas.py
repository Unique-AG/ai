import pytest
from pydantic import ValidationError
from unique_search_proxy_core.crawlers import parse_crawler_config
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.basic.schema import BasicCrawlerConfig
from unique_search_proxy_core.schema import ProxyErrorCode, WebSearchResult
from unique_search_proxy_core.search_engines import (
    SearchEngineType,
    parse_search_engine_config,
)
from unique_search_proxy_core.search_engines.brave.schema import BraveConfig
from unique_search_proxy_core.search_engines.google.schema import GoogleConfig


class TestWebSearchResult:
    @pytest.mark.ai
    def test_basic_creation(self) -> None:
        r = WebSearchResult(url="https://a.com", title="A", snippet="snip")
        assert r.url == "https://a.com"
        assert r.title == "A"
        assert r.snippet == "snip"
        assert r.content == ""

    @pytest.mark.ai
    def test_camel_case_deserialization(self) -> None:
        data = {"url": "u", "title": "t", "snippet": "s", "content": "c"}
        r = WebSearchResult.model_validate(data)
        assert r.content == "c"


class TestProviderConfig:
    @pytest.mark.ai
    def test_google_config_discriminator(self) -> None:
        config = parse_search_engine_config(
            {"engine": "google", "dateRestrict": "d7", "gl": "ch"},
        )
        assert isinstance(config, GoogleConfig)
        assert config.engine == SearchEngineType.GOOGLE
        assert config.date_restrict is not None
        assert config.date_restrict.value == "d7"
        assert config.gl is not None
        assert config.gl.value == "ch"

    @pytest.mark.ai
    def test_brave_config_discriminator(self) -> None:
        config = parse_search_engine_config(
            {
                "engine": "brave",
                "country": {"expose": True, "value": "CH"},
                "freshness": "pw",
            },
        )
        assert isinstance(config, BraveConfig)
        assert config.engine == SearchEngineType.BRAVE
        assert config.country is not None
        assert config.country.value == "CH"
        assert config.freshness is not None
        assert config.freshness.expose is False
        assert config.freshness.value == "pw"

    @pytest.mark.ai
    def test_unknown_engine_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            parse_search_engine_config({"engine": "unknown-engine"})

    @pytest.mark.ai
    def test_crawler_config(self) -> None:
        config = parse_crawler_config({"crawler": CrawlerType.BASIC.value})
        assert isinstance(config, BasicCrawlerConfig)
        assert config.crawler == CrawlerType.BASIC


class TestProxyErrorCode:
    @pytest.mark.ai
    def test_engine_not_configured_value(self) -> None:
        assert ProxyErrorCode.ENGINE_NOT_CONFIGURED == "ENGINE_NOT_CONFIGURED"
