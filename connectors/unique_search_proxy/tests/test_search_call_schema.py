import pytest
from fastapi.testclient import TestClient

from unique_search_proxy.web.app import create_app
from unique_search_proxy.web.core.search_engines.call_schema import (
    resolve_search_call_schema,
)


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client


class TestResolveSearchCallSchema:
    @pytest.mark.ai
    def test_query_and_fetch_size_in_schema(self, client: TestClient) -> None:
        _ = client
        descriptor = resolve_search_call_schema("google")
        assert descriptor.engine == "google"
        assert descriptor.snippet_only is True
        assert descriptor.mode == "standard"
        properties = descriptor.call_schema.get("properties", {})
        assert "query" in properties
        assert "fetchSize" not in properties
        assert "dateRestrict" not in properties

    @pytest.mark.ai
    def test_expose_without_value_accepted_and_llm_fields_required(
        self,
        client: TestClient,
    ) -> None:
        resp = client.post(
            "/v1/configuration/search-engines/google/call-schema",
            json={
                "engine": "google",
                "fetchSize": 10,
                "safe": "active",
                "gl": {"expose": True},
            },
        )
        assert resp.status_code == 200
        call_schema = resp.json()["callSchema"]
        assert set(call_schema["required"]) == {"query", "gl"}
        assert "default" not in call_schema["properties"]["gl"]
        assert "default" not in call_schema["properties"]["query"]

    @pytest.mark.ai
    def test_strict_false_allows_optional_llm_fields(
        self,
        client: TestClient,
    ) -> None:
        resp = client.post(
            "/v1/configuration/search-engines/google/call-schema?strict=false",
            json={
                "engine": "google",
                "hl": {"expose": True},
            },
        )
        assert resp.status_code == 200
        call_schema = resp.json()["callSchema"]
        assert "hl" in call_schema["properties"]
        assert "hl" not in call_schema.get("required", [])
        hl_prop = call_schema["properties"]["hl"]
        assert hl_prop.get("default") is None

    @pytest.mark.ai
    def test_strict_false_inherits_admin_default_on_exposed_field(
        self,
        client: TestClient,
    ) -> None:
        resp = client.post(
            "/v1/configuration/search-engines/google/call-schema?strict=false",
            json={
                "engine": "google",
                "fetchSize": 10,
                "safe": "active",
                "gl": {"expose": True, "value": "ch"},
            },
        )
        assert resp.status_code == 200
        call_schema = resp.json()["callSchema"]
        assert call_schema["properties"]["gl"]["default"] == "ch"

    @pytest.mark.ai
    def test_expose_fields_from_config_appear_in_schema(
        self,
        client: TestClient,
    ) -> None:
        _ = client
        descriptor = resolve_search_call_schema(
            "google",
            config={
                "engine": "google",
                "gl": {"expose": True, "value": "ch"},
                "dateRestrict": {"expose": False, "value": "d7"},
            },
        )
        properties = descriptor.call_schema.get("properties", {})
        assert "query" in properties
        assert "fetchSize" not in properties
        assert "gl" in properties
        assert "dateRestrict" not in properties


class TestSearchCallSchemaEndpoint:
    @pytest.mark.ai
    def test_post_call_schema_for_google(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/configuration/search-engines/google/call-schema",
            json={
                "engine": "google",
                "gl": {"expose": True, "value": "ch"},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["engine"] == "google"
        assert body["snippetOnly"] is True
        assert body["mode"] == "standard"
        assert "query" in body["callSchema"]["properties"]
        assert "fetchSize" not in body["callSchema"]["properties"]
        assert "gl" in body["callSchema"]["properties"]

    @pytest.mark.ai
    def test_unknown_engine_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/configuration/search-engines/brave/call-schema",
            json={"engine": "google"},
        )
        assert resp.status_code == 422

    @pytest.mark.ai
    def test_config_engine_mismatch_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/configuration/search-engines/brave/call-schema",
            json={"engine": "google"},
        )
        assert resp.status_code == 422
