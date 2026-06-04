import pytest
from fastapi.testclient import TestClient
from unique_search_proxy_core.errors import (
    BadRequestProxyError,
    EmptySearchResultsError,
    EngineNotConfiguredError,
    ForbiddenTargetError,
    RateLimitedError,
    UpstreamError,
    UpstreamTimeoutError,
    ValidationProxyError,
)
from unique_search_proxy_core.schema import ProxyErrorCode

from unique_search_proxy_client.web.app import create_app
from unique_search_proxy_client.web.error_handlers import proxy_error_response


@pytest.mark.ai
@pytest.mark.parametrize(
    ("exc", "status", "code"),
    [
        (BadRequestProxyError("bad"), 400, ProxyErrorCode.BAD_REQUEST),
        (ValidationProxyError("invalid"), 422, ProxyErrorCode.VALIDATION_ERROR),
        (ForbiddenTargetError("blocked"), 403, ProxyErrorCode.FORBIDDEN_TARGET),
        (
            RateLimitedError("slow", retry_after_seconds=30),
            429,
            ProxyErrorCode.RATE_LIMITED,
        ),
        (UpstreamError("upstream"), 502, ProxyErrorCode.UPSTREAM_ERROR),
        (EngineNotConfiguredError("google"), 503, ProxyErrorCode.ENGINE_NOT_CONFIGURED),
        (UpstreamTimeoutError("timeout"), 504, ProxyErrorCode.UPSTREAM_TIMEOUT),
        (
            EmptySearchResultsError("none", engine="google"),
            404,
            ProxyErrorCode.EMPTY_SEARCH_RESULTS,
        ),
    ],
)
def test_proxy_error_status_mapping(exc, status, code) -> None:
    response = proxy_error_response(exc)
    assert response.status_code == status
    body = response.body.decode()
    assert code.value in body


@pytest.mark.ai
def test_rate_limited_sets_retry_after_header() -> None:
    response = proxy_error_response(
        RateLimitedError("slow", retry_after_seconds=42),
    )
    assert response.headers.get("Retry-After") == "42"


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client


class TestV1StructuredErrors:
    @pytest.mark.ai
    def test_unknown_search_engine_returns_422(self, client: TestClient) -> None:
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
        assert body["error"]["code"] == ProxyErrorCode.VALIDATION_ERROR.value

    @pytest.mark.ai
    def test_unregistered_crawler_returns_503(self, client: TestClient) -> None:
        from unique_search_proxy_client.web.core.registry import _CRAWLER_REGISTRY

        _CRAWLER_REGISTRY.clear()
        resp = client.post(
            "/v1/crawl",
            json={
                "urls": ["https://example.com"],
                "config": {"crawler": "basic"},
            },
        )
        assert resp.status_code == 503
        assert resp.json()["error"]["crawler"] == "basic"

    @pytest.mark.ai
    def test_validation_error_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/search",
            json={"engine": "google", "query": "", "fetchSize": 10},
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == ProxyErrorCode.VALIDATION_ERROR.value
