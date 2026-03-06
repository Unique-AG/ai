import logging
from unittest.mock import patch

import pytest
from app import ErrorResponse, HealthCheckFilter, SearchResponse, app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy"}


class TestSearchEndpoint:
    def test_missing_body_returns_400(self, client):
        resp = client.post("/search")
        assert resp.status_code == 422 or resp.status_code == 400

    def test_invalid_search_engine_returns_error(self, client):
        resp = client.post(
            "/search",
            json={"searchEngine": "invalid", "query": "test", "params": {}},
        )
        assert resp.status_code in (400, 422)

    def test_successful_google_search(self, client, google_search_env):
        async def mock_search(self, query):
            from core.schema import WebSearchResult

            return [WebSearchResult(url="https://a.com", title="A", snippet="s")]

        with patch("core.google_search.search.GoogleSearch.search", new=mock_search):
            resp = client.post(
                "/search",
                json={
                    "searchEngine": "google",
                    "query": "test query",
                    "params": {},
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) == 1


class TestExceptionHandlers:
    def test_generic_exception_returns_500(self, google_search_env):
        async def boom_search(self, query):
            raise RuntimeError("boom")

        with (
            TestClient(app, raise_server_exceptions=False) as c,
            patch("core.google_search.search.GoogleSearch.search", new=boom_search),
        ):
            resp = c.post(
                "/search",
                json={
                    "searchEngine": "google",
                    "query": "test",
                    "params": {},
                },
            )
        assert resp.status_code == 500
        assert "error" in resp.json()


class TestHealthCheckFilter:
    def test_filters_health_get(self):
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

    def test_passes_non_health(self):
        f = HealthCheckFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='POST /search HTTP/1.1" 200',
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is True


class TestResponseModels:
    def test_search_response(self):
        from core.schema import WebSearchResult

        r = SearchResponse(results=[WebSearchResult(url="u", title="t", snippet="s")])
        assert len(r.results) == 1

    def test_error_response_default_status(self):
        e = ErrorResponse(error="something went wrong")
        assert e.status == "failed"
        assert e.error == "something went wrong"
