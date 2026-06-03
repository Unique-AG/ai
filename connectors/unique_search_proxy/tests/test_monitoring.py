import pytest
from fastapi.testclient import TestClient

from unique_search_proxy.web.app import create_app
from unique_search_proxy.web.monitoring.settings import PrometheusSettingsForTests


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("PROMETHEUS_ENABLED", "true")
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def client_metrics_disabled(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from unique_search_proxy.web.monitoring.settings import PrometheusSettingsForTests

    monkeypatch.setattr(
        "unique_search_proxy.web.monitoring.settings.prometheus_settings",
        PrometheusSettingsForTests(enabled=False),
    )
    with TestClient(create_app()) as test_client:
        yield test_client


class TestMetricsEndpoint:
    @pytest.mark.ai
    def test_metrics_returns_prometheus_text(self, client: TestClient) -> None:
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        body = resp.text
        assert "python_http_requests_total" in body
        assert "unique_search_proxy" in body

    @pytest.mark.ai
    def test_metrics_disabled_returns_404(
        self, client_metrics_disabled: TestClient
    ) -> None:
        resp = client_metrics_disabled.get("/metrics")
        assert resp.status_code == 404

    @pytest.mark.ai
    def test_search_increments_proxy_error_metric(self, client: TestClient) -> None:
        client.post(
            "/v1/search",
            json={"config": {"engine": "google"}, "call": {"query": "test"}},
        )
        metrics = client.get("/metrics").text
        assert "unique_search_proxy_proxy_errors_total" in metrics
        assert "ENGINE_NOT_CONFIGURED" in metrics


class TestPrometheusSettings:
    @pytest.mark.ai
    def test_prometheus_enabled_default(self) -> None:
        settings = PrometheusSettingsForTests()
        assert settings.enabled is True
