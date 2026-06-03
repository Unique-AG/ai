import pytest

from unique_search_proxy.web.core.schema import (
    CrawlerConfig,
    ProxyErrorCode,
    SearchEngineConfig,
    WebSearchResult,
)


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
    def test_search_engine_config(self) -> None:
        config = SearchEngineConfig.model_validate(
            {"engine": "google", "exposedFields": ["query"]},
        )
        assert config.engine == "google"
        assert config.exposed_fields == ["query"]

    @pytest.mark.ai
    def test_crawler_config(self) -> None:
        config = CrawlerConfig.model_validate({"crawler": "basic"})
        assert config.crawler == "basic"


class TestProxyErrorCode:
    @pytest.mark.ai
    def test_engine_not_configured_value(self) -> None:
        assert ProxyErrorCode.ENGINE_NOT_CONFIGURED == "ENGINE_NOT_CONFIGURED"
