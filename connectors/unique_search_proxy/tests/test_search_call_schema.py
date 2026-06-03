import pytest
from fastapi.testclient import TestClient

from unique_search_proxy.web.app import create_app
from unique_search_proxy.web.core.search_engines.call_schema import (
    resolve_search_call_schema,
)
from unique_search_proxy.web.core.search_engines.google.schema import GoogleConfig


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client


class TestResolveSearchCallSchema:
    @pytest.mark.ai
    def test_query_only_projection(self) -> None:
        descriptor = resolve_search_call_schema(GoogleConfig())
        assert descriptor.engine == "google"
        assert descriptor.snippet_only is True
        assert descriptor.mode == "standard"
        properties = descriptor.call_schema.get("properties", {})
        assert "query" in properties
        assert "dateRestrict" not in properties

    @pytest.mark.ai
    def test_exposed_fields_appear_in_schema(self) -> None:
        config = GoogleConfig(gl="us", exposed_fields=["gl", "dateRestrict"])
        descriptor = resolve_search_call_schema(config)
        properties = descriptor.call_schema.get("properties", {})
        assert "query" in properties
        assert "gl" in properties
        assert "dateRestrict" in properties


class TestSearchCallSchemaEndpoint:
    @pytest.mark.ai
    def test_returns_call_schema_for_google(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/search/call-schema",
            json={
                "config": {
                    "engine": "google",
                    "exposedFields": ["gl"],
                    "gl": "ch",
                },
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["engine"] == "google"
        assert body["snippetOnly"] is True
        assert body["mode"] == "standard"
        assert "query" in body["callSchema"]["properties"]
        assert "gl" in body["callSchema"]["properties"]

    @pytest.mark.ai
    def test_unknown_engine_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/search/call-schema",
            json={"config": {"engine": "brave"}},
        )
        assert resp.status_code == 422

    @pytest.mark.ai
    def test_invalid_exposed_field_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/search/call-schema",
            json={
                "config": {
                    "engine": "google",
                    "exposedFields": ["fetchSize"],
                },
            },
        )
        assert resp.status_code == 422
