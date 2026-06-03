import logging

import pytest
from fastapi.testclient import TestClient

from unique_search_proxy.web.app import HealthCheckFilter, create_app


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client


class TestHealthEndpoint:
    @pytest.mark.ai
    def test_health_returns_ok(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy"}


class TestV1SearchEndpoint:
    @pytest.mark.ai
    def test_missing_body_returns_422(self, client: TestClient) -> None:
        resp = client.post("/v1/search")
        assert resp.status_code == 422

    @pytest.mark.ai
    def test_unknown_engine_returns_structured_422(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/search",
            json={
                "engine": "unknown-engine",
                "query": "test",
                "fetchSize": 10,
            },
        )
        assert resp.status_code == 422
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "VALIDATION_ERROR"


class TestHealthCheckFilter:
    @pytest.mark.ai
    def test_filters_health_get(self) -> None:
        f = HealthCheckFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='GET /health HTTP/1.1" 200',
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is False

    @pytest.mark.ai
    def test_passes_non_health(self) -> None:
        f = HealthCheckFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='POST /v1/search HTTP/1.1" 200',
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is True

    @pytest.mark.ai
    def test_filters_metrics_get(self) -> None:
        f = HealthCheckFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='GET /metrics HTTP/1.1" 200',
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is False
