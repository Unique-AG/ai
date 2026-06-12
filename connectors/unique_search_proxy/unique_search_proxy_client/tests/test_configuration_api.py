import pytest
from fastapi.testclient import TestClient
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.providers.schema import (
    provider_config_json_schema,
    search_engines_config_json_schema,
)

from unique_search_proxy_client.web.app import create_app


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client


class TestProviderConfigSchemaCore:
    @pytest.mark.ai
    def test_google_config_schema_has_engine_discriminator(self) -> None:
        schema = provider_config_json_schema("search_engine", "google")
        properties = schema.get("properties", {})
        assert "engine" in properties
        assert properties["engine"].get("const") == "google"

    @pytest.mark.ai
    def test_union_schema_includes_registered_engines(self) -> None:
        schema = search_engines_config_json_schema()
        defs = schema.get("$defs", {})
        assert "GoogleConfig" in defs
        assert "BraveConfig" in defs
        any_of = schema.get("anyOf", [])
        refs = {item["$ref"] for item in any_of}
        assert "#/$defs/GoogleConfig" in refs
        assert "#/$defs/BraveConfig" in refs


class TestConfigurationEndpoints:
    @pytest.mark.ai
    def test_list_providers(self, client: TestClient) -> None:
        resp = client.get("/v1/configuration/providers")
        assert resp.status_code == 200
        body = resp.json()
        assert "google" in body["searchEngines"]
        assert "brave" in body["searchEngines"]
        assert "perplexity" in body["searchEngines"]
        assert CrawlerType.BASIC.value in body["crawlers"]
        assert CrawlerType.TAVILY.value in body["crawlers"]
        assert CrawlerType.JINA.value in body["crawlers"]
        assert CrawlerType.FIRECRAWL.value in body["crawlers"]
