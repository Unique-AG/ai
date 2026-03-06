import logging
from unittest.mock import patch

import pytest
from app import ErrorResponse, HealthCheckFilter, SearchResponse, app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    @pytest.mark.ai
    def test_health_returns_ok(self, client):
        """
        Purpose: Verify the /health endpoint returns 200 with healthy status.
        Why this matters: Health checks are used by load balancers and orchestrators.
        Setup summary: GET /health and assert response status and body.
        """
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy"}


class TestSearchEndpoint:
    @pytest.mark.ai
    def test_missing_body_returns_400(self, client):
        """
        Purpose: Verify missing request body returns a 4xx error.
        Why this matters: Malformed requests must be rejected with clear errors.
        Setup summary: POST /search with no body and assert 400 or 422.
        """
        resp = client.post("/search")
        assert resp.status_code == 422 or resp.status_code == 400

    @pytest.mark.ai
    def test_invalid_search_engine_returns_error(self, client):
        """
        Purpose: Verify an invalid search engine type returns an error.
        Why this matters: Only supported engines should be accepted by the API.
        Setup summary: POST with searchEngine="invalid" and assert 4xx.
        """
        resp = client.post(
            "/search",
            json={"searchEngine": "invalid", "query": "test", "params": {}},
        )
        assert resp.status_code in (400, 422)

    @pytest.mark.ai
    def test_successful_google_search(self, client, google_search_env):
        """
        Purpose: Verify a valid Google search request returns 200 with results.
        Why this matters: This is the primary happy-path for the search API.
        Setup summary: Mock GoogleSearch.search, POST a valid request, assert 200 and results.
        """
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
    @pytest.mark.ai
    def test_generic_exception_returns_500(self, google_search_env):
        """
        Purpose: Verify unhandled exceptions are caught and returned as 500 JSON errors.
        Why this matters: Uncaught exceptions must not leak stack traces to clients.
        Setup summary: Mock search to raise RuntimeError, assert 500 and error key in body.
        """
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
    @pytest.mark.ai
    def test_filters_health_get(self):
        """
        Purpose: Verify the filter suppresses GET /health log records.
        Why this matters: Health check logs create excessive noise in production.
        Setup summary: Create a log record matching GET /health and assert it is filtered out.
        """
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
    def test_passes_non_health(self):
        """
        Purpose: Verify the filter allows non-health log records through.
        Why this matters: All other endpoint logs must be preserved for observability.
        Setup summary: Create a log record for POST /search and assert it passes.
        """
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
    @pytest.mark.ai
    def test_search_response(self):
        """
        Purpose: Verify SearchResponse wraps a list of WebSearchResult objects.
        Why this matters: The response model defines the API contract for /search.
        Setup summary: Construct a SearchResponse with one result and assert its length.
        """
        from core.schema import WebSearchResult

        r = SearchResponse(results=[WebSearchResult(url="u", title="t", snippet="s")])
        assert len(r.results) == 1

    @pytest.mark.ai
    def test_error_response_default_status(self):
        """
        Purpose: Verify ErrorResponse defaults to "failed" status.
        Why this matters: Consistent error responses simplify client error handling.
        Setup summary: Construct an ErrorResponse and assert default status.
        """
        e = ErrorResponse(error="something went wrong")
        assert e.status == "failed"
        assert e.error == "something went wrong"
