"""Attribution: unattributed handling, usage records and the request counter."""

from __future__ import annotations

from collections.abc import AsyncIterator, Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from unique_search_proxy_core.context import (
    ENTRY_POINT_HEADER,
    EntryPoint,
    RequestContext,
)
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.errors import UpstreamError
from unique_search_proxy_core.schema import (
    AgentSearchResponse,
    SearchEngineRaw,
    WebSearchResult,
    WebSearchResults,
)
from unique_search_proxy_core.usage import UsageRecord
from unique_toolkit.monitoring.registry import REGISTRY

from unique_search_proxy_client.web.app import create_app
from unique_search_proxy_client.web.settings.app import AppSettings

pytestmark = pytest.mark.ai

_SEARCH_BODY = {"engine": "google", "query": "secret query", "fetchSize": 1}
_ATTRIBUTED = RequestContext(
    company_id="123456789012345678",
    user_id="987654321098765432",
    chat_id="chat-1",
    message_id="msg-1",
    entry_point=EntryPoint.PUBLIC_API,
)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def usage_records(monkeypatch: pytest.MonkeyPatch) -> list[UsageRecord]:
    records: list[UsageRecord] = []
    monkeypatch.setattr(
        "unique_search_proxy_client.web.usage.record_usage",
        records.append,
    )
    return records


@pytest.fixture
def google_search_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "test-cx")

    async def fake_search(
        self: object,
        request: object,
    ) -> tuple[SearchEngineRaw, WebSearchResults]:
        return SearchEngineRaw(pages=[]), WebSearchResults(
            results=[
                WebSearchResult(url="https://example.com", title="t", snippet="s")
            ],
        )

    monkeypatch.setattr(
        "unique_search_proxy_client.web.core.search_engines.google.service.GoogleSearchService.search",
        fake_search,
    )


def _sample(name: str, **labels: str) -> float:
    return REGISTRY.get_sample_value(f"unique_search_proxy_{name}", labels) or 0.0


class TestUnattributedRequests:
    def test_local_context_is_counted_by_entry_point_and_still_served(
        self,
        client: TestClient,
        google_search_ok: None,
    ) -> None:
        before = _sample("unattributed_requests_total", entry_point="chat_tool")

        response = client.post(
            "/v1/search",
            headers={ENTRY_POINT_HEADER: "chat_tool"},
            json=_SEARCH_BODY,
        )

        assert response.status_code == 200
        assert (
            _sample("unattributed_requests_total", entry_point="chat_tool")
            == before + 1
        )

    def test_configuration_route_skips_attribution_check(
        self,
        client: TestClient,
    ) -> None:
        before = _sample("unattributed_requests_total", entry_point="unknown")

        response = client.get("/v1/configuration/providers")

        assert response.status_code == 200
        assert _sample("unattributed_requests_total", entry_point="unknown") == before

    def test_attributed_request_is_not_counted(
        self,
        client: TestClient,
        google_search_ok: None,
    ) -> None:
        before = _sample("unattributed_requests_total", entry_point="public_api")

        client.post("/v1/search", headers=_ATTRIBUTED.to_headers(), json=_SEARCH_BODY)

        assert (
            _sample("unattributed_requests_total", entry_point="public_api") == before
        )

    def test_reject_setting_returns_400_naming_headers_without_values(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_search_proxy_client.web.middleware.context.app_settings",
            AppSettings(reject_unattributed_requests=True),
        )
        headers = _ATTRIBUTED.model_copy(update={"user_id": "junk-user"}).to_headers()

        response = client.post("/v1/search", headers=headers, json=_SEARCH_BODY)

        assert response.status_code == 400
        assert "x-unique-user-id" in response.text
        assert "junk-user" not in response.text
        assert "x-unique-company-id" not in response.text

    def test_reject_setting_lets_attributed_requests_through(
        self,
        client: TestClient,
        google_search_ok: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "unique_search_proxy_client.web.middleware.context.app_settings",
            AppSettings(reject_unattributed_requests=True),
        )

        response = client.post(
            "/v1/search",
            headers=_ATTRIBUTED.to_headers(),
            json=_SEARCH_BODY,
        )

        assert response.status_code == 200


class TestUsageRecording:
    def test_search_success_records_attributed_usage(
        self,
        client: TestClient,
        google_search_ok: None,
        usage_records: list[UsageRecord],
    ) -> None:
        labels = {
            "company_id": _ATTRIBUTED.company_id,
            "entry_point": "public_api",
            "endpoint": "search",
            "provider": "google",
            "status": "success",
        }
        before = _sample("requests_total", **labels)

        client.post("/v1/search", headers=_ATTRIBUTED.to_headers(), json=_SEARCH_BODY)

        [record] = usage_records
        assert (record.company_id, record.user_id, record.chat_id) == (
            _ATTRIBUTED.company_id,
            _ATTRIBUTED.user_id,
            "chat-1",
        )
        assert record.entry_point is EntryPoint.PUBLIC_API
        assert record.message_id == "msg-1"
        assert (record.endpoint, record.provider, record.units) == (
            "search",
            "google",
            1,
        )
        assert record.status == "success"
        assert "secret query" not in record.model_dump_json()
        assert _sample("requests_total", **labels) == before + 1

    def test_provider_failure_records_error_status(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        usage_records: list[UsageRecord],
    ) -> None:
        monkeypatch.delenv("GOOGLE_SEARCH_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_SEARCH_ENGINE_ID", raising=False)

        response = client.post(
            "/v1/search",
            headers=_ATTRIBUTED.to_headers(),
            json=_SEARCH_BODY,
        )

        assert response.status_code != 200
        [record] = usage_records
        assert record.status == "error"

    def test_unattributed_request_uses_placeholder_company_label(
        self,
        client: TestClient,
        google_search_ok: None,
    ) -> None:
        labels = {
            "company_id": "unattributed",
            "entry_point": "unknown",
            "endpoint": "search",
            "provider": "google",
            "status": "success",
        }
        before = _sample("requests_total", **labels)

        client.post(
            "/v1/search",
            headers={"x-unique-company-id": "junk-company"},
            json=_SEARCH_BODY,
        )

        assert _sample("requests_total", **labels) == before + 1

    def test_crawl_with_every_url_blocked_records_zero_units(
        self,
        client: TestClient,
        usage_records: list[UsageRecord],
    ) -> None:
        response = client.post(
            "/v1/crawl",
            headers=_ATTRIBUTED.to_headers(),
            json={
                "urls": ["http://127.0.0.1:8080", "http://127.0.0.1:9090"],
                "crawler": CrawlerType.BASIC.value,
                "timeout": 10,
                "contentTypes": {"html": True},
            },
        )

        assert response.status_code == 200
        [record] = usage_records
        assert (record.endpoint, record.provider) == ("crawl", CrawlerType.BASIC.value)
        assert record.units == 0
        assert record.status == "success"
        assert "127.0.0.1" not in record.model_dump_json()

    def test_agent_search_records_one_unit(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        usage_records: list[UsageRecord],
    ) -> None:
        monkeypatch.setenv("BING_AGENT_ENDPOINT", "https://example.azure.com")
        monkeypatch.setenv(
            "BING_AGENT_BING_RESOURCE_CONNECTION_STRING", "/subscriptions/x"
        )
        with patch(
            "unique_search_proxy_client.web.api.v1.agent_search.get_agent_engine_service",
        ) as get_service:
            get_service.return_value.search = AsyncMock(
                return_value=AgentSearchResponse(
                    engine="bing", query="q", answer="a", raw={}
                ),
            )
            response = client.post(
                "/v1/agent-search",
                headers=_ATTRIBUTED.to_headers(),
                json={"engine": "bing", "query": "q", "fetchSize": 5, "timeout": 120},
            )

        assert response.status_code == 200
        [record] = usage_records
        assert (record.endpoint, record.provider, record.units, record.status) == (
            "agent_search",
            "bing",
            1,
            "success",
        )

    @pytest.mark.parametrize(
        ("fails", "status"),
        [(False, "success"), (True, "error")],
    )
    def test_agent_search_stream_records_usage_when_stream_ends(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        usage_records: list[UsageRecord],
        fails: bool,
        status: str,
    ) -> None:
        async def stream(_body: object) -> AsyncIterator[str]:
            if fails:
                raise UpstreamError("boom")
            return
            yield

        monkeypatch.setenv("BING_AGENT_ENDPOINT", "https://example.azure.com")
        monkeypatch.setenv(
            "BING_AGENT_BING_RESOURCE_CONNECTION_STRING", "/subscriptions/x"
        )
        with patch(
            "unique_search_proxy_client.web.api.v1.agent_search.get_agent_engine_service",
        ) as get_service:
            get_service.return_value.stream = stream
            client.post(
                "/v1/agent-search/stream",
                headers=_ATTRIBUTED.to_headers(),
                json={"engine": "bing", "query": "q", "fetchSize": 5, "timeout": 120},
            )

        [record] = usage_records
        assert (record.endpoint, record.status) == ("agent_search", status)
        assert (record.company_id, record.user_id, record.entry_point) == (
            _ATTRIBUTED.company_id,
            _ATTRIBUTED.user_id,
            EntryPoint.PUBLIC_API,
        )

    def test_agent_search_stream_setup_failure_records_error(
        self,
        client: TestClient,
        usage_records: list[UsageRecord],
    ) -> None:
        with patch(
            "unique_search_proxy_client.web.api.v1.agent_search.get_agent_engine_service",
            side_effect=RuntimeError("no engine"),
        ):
            response = client.post(
                "/v1/agent-search/stream",
                headers=_ATTRIBUTED.to_headers(),
                json={"engine": "bing", "query": "q", "fetchSize": 5, "timeout": 120},
            )

        assert response.status_code == 502
        [record] = usage_records
        assert (record.endpoint, record.status) == ("agent_search", "error")
