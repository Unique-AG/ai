import pytest
from fastapi.testclient import TestClient

from unique_search_proxy.web.app import create_app


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client


class TestHealthEndpoints:
    @pytest.mark.ai
    def test_health_returns_ok(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy"}

    @pytest.mark.ai
    def test_ready_reports_pool_and_empty_registries(self, client: TestClient) -> None:
        resp = client.get("/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ready"
        assert body["httpClient"] == "ok"
        assert body["searchEngines"] == ["google"]
        assert body["crawlers"] == ["basic"]
