import pytest
from fastapi.testclient import TestClient

from unique_search_proxy_client.web.app import create_app
from unique_search_proxy_client.web.core.provider_config_schema import (
    provider_config_json_schema,
    registered_search_engines_config_json_schema,
)


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
    def test_union_schema_is_object_with_properties(self) -> None:
        schema = registered_search_engines_config_json_schema()
        assert schema.get("type") == "object"
        assert "engine" in schema.get("properties", {})


class TestConfigurationEndpoints:
    @pytest.mark.ai
    def test_list_providers(self, client: TestClient) -> None:
        resp = client.get("/v1/configuration/providers")
        assert resp.status_code == 200
        body = resp.json()
        assert "google" in body["searchEngines"]
        assert "basic" in body["crawlers"]

    @pytest.mark.ai
    def test_search_engine_json_schema(self, client: TestClient) -> None:
        resp = client.get("/v1/configuration/search-engines/google/json-schema")
        assert resp.status_code == 200
        body = resp.json()
        assert body["providerId"] == "google"
        assert body["jsonSchema"]["properties"]["engine"]["const"] == "google"

    @pytest.mark.ai
    def test_search_engine_default_config(self, client: TestClient) -> None:
        resp = client.get("/v1/configuration/search-engines/google/default-config")
        assert resp.status_code == 200
        body = resp.json()
        assert body["defaultConfig"]["engine"] == "google"
        assert "fetchSize" in body["defaultConfig"]

    @pytest.mark.ai
    def test_crawler_json_schema(self, client: TestClient) -> None:
        resp = client.get("/v1/configuration/crawlers/basic/json-schema")
        assert resp.status_code == 200
        body = resp.json()
        assert body["providerId"] == "basic"
        assert body["jsonSchema"]["properties"]["crawler"]["const"] == "basic"

    @pytest.mark.ai
    def test_unknown_engine_returns_503(self, client: TestClient) -> None:
        resp = client.get("/v1/configuration/search-engines/brave/json-schema")
        assert resp.status_code == 503

    @pytest.mark.ai
    def test_union_search_engines_schema(self, client: TestClient) -> None:
        resp = client.get("/v1/configuration/search-engines/json-schema")
        assert resp.status_code == 200
        assert "jsonSchema" in resp.json()
