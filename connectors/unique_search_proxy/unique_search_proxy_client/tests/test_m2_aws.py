from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from botocore.credentials import Credentials
from botocore.exceptions import ClientError, MissingDependencyException
from unique_search_proxy_core.errors import (
    EmptySearchResultsError,
    EngineNotConfiguredError,
    RateLimitedError,
    UpstreamError,
    ValidationProxyError,
)
from unique_search_proxy_core.search_engines.aws.schema import (
    AwsConfig,
    AwsSearchRequest,
)

from unique_search_proxy_client.web.core.search_engines.aws import service
from unique_search_proxy_client.web.core.search_engines.aws.service import (
    AwsSearchService,
    resolve_aws_credentials,
)


@pytest.fixture(autouse=True)
def _fresh_aws_session() -> None:
    service._aws_session.cache_clear()


def _request(**fields: Any) -> AwsSearchRequest:
    return AwsSearchRequest.model_validate(
        {
            "query": "Swiss National Bank",
            "fetch_size": 2,
            "timeout": 30,
            **fields,
        },
    )


def _credentials() -> Credentials:
    return Credentials("AKIDEXAMPLE", "secret", "token")


@pytest.fixture
def aws_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Pin region and endpoint so AWS_SEARCH_* in the runner's env cannot change them.
    monkeypatch.setattr(
        service,
        "credentials",
        service.credentials.model_copy(
            update={
                "region": "us-east-1",
                "api_endpoint": "https://bedrock-agentcore.us-east-1.amazonaws.com",
            }
        ),
    )
    monkeypatch.setattr(
        "unique_search_proxy_client.web.core.search_engines.aws.service.resolve_aws_credentials",
        _credentials,
    )


class TestAwsSearchService:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search_signs_and_maps_results(self, aws_env: None) -> None:
        seen: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["authorization"] = request.headers["Authorization"]
            seen["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "url": "https://snb.ch/rate",
                            "title": "SNB",
                            "text": "The policy rate is unchanged.",
                            "publishedAt": "2026-09-01T00:00:00Z",
                        },
                        {"text": "dropped because it has no url"},
                        {"url": "https://example.com/untitled", "text": "no title"},
                    ],
                },
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            _raw, curated = await AwsSearchService(http_client=client).search(
                _request(
                    include_domains=["snb.ch"],
                    published_after=datetime(2026, 8, 1, tzinfo=UTC),
                ),
            )

        assert seen["url"] == (
            "https://bedrock-agentcore.us-east-1.amazonaws.com/web-search/web-search.v1/invoke"
        )
        assert seen["authorization"].startswith("AWS4-HMAC-SHA256")
        assert seen["body"]["searchQuery"] == "Swiss National Bank"
        assert seen["body"]["maxResults"] == 2
        assert seen["body"]["filters"]["domainFilter"] == {"include": ["snb.ch"]}
        assert seen["body"]["filters"]["publishedDateFilter"]["publishedAfter"] == (
            "2026-08-01T00:00:00Z"
        )
        assert [item.url for item in curated.results] == [
            "https://snb.ch/rate",
            "https://example.com/untitled",
        ]
        assert curated.results[0].snippet == "The policy rate is unchanged."
        assert curated.results[1].title == ""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_query_over_200_characters_is_rejected(self, aws_env: None) -> None:
        with pytest.raises(ValueError, match="200"):
            _request(query="a" * 201)
        unvalidated = AwsSearchRequest.model_construct(
            **{**_request().model_dump(), "query": "a" * 201}
        )
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, json={"results": []}),
        )
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(ValidationProxyError):
                await AwsSearchService(http_client=client).search(unvalidated)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_access_denied_is_not_configured(self, aws_env: None) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(403, json={"message": "denied"}),
        )
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(EngineNotConfiguredError):
                await AwsSearchService(http_client=client).search(_request())

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_throttling_is_rate_limited(self, aws_env: None) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(429, json={"message": "slow down"}),
        )
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(RateLimitedError):
                await AwsSearchService(http_client=client).search(_request())

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_rejected_request_is_a_validation_error(self, aws_env: None) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                400,
                json={"message": "publishedAfter is after publishedBefore"},
                headers={"x-amzn-ErrorType": "ValidationException"},
            ),
        )
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(ValidationProxyError) as exc_info:
                await AwsSearchService(http_client=client).search(_request())
        assert exc_info.value.retryable is False

    @pytest.mark.ai
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "response",
        [
            httpx.Response(200, text="<html>gateway</html>"),
            httpx.Response(200, json=[{"url": "https://www.snb.ch/"}]),
            httpx.Response(302, headers={"location": "https://example.com/"}),
        ],
    )
    async def test_malformed_response_is_an_upstream_error(
        self, aws_env: None, response: httpx.Response
    ) -> None:
        transport = httpx.MockTransport(lambda request: response)
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(UpstreamError):
                await AwsSearchService(http_client=client).search(_request())

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_results_without_urls_are_empty(self, aws_env: None) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"results": [{"text": "no url"}]},
            ),
        )
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(EmptySearchResultsError):
                await AwsSearchService(http_client=client).search(_request())

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_missing_login_dependency_is_not_configured(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def raise_missing() -> None:
            raise MissingDependencyException(msg="install botocore[crt]")

        monkeypatch.setattr(
            "unique_search_proxy_client.web.core.search_engines.aws.service.get_session",
            lambda: type(
                "Session", (), {"get_credentials": staticmethod(raise_missing)}
            )(),
        )
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, json={"results": []}),
        )
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(EngineNotConfiguredError):
                await AwsSearchService(http_client=client).search(_request())

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            ("AccessDenied", EngineNotConfiguredError),
            ("InvalidIdentityToken", EngineNotConfiguredError),
            ("ExpiredTokenException", EngineNotConfiguredError),
            ("Throttling", RateLimitedError),
            ("IDPCommunicationError", UpstreamError),
        ],
    )
    def test_sts_rejection_maps_to_a_proxy_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        code: str,
        expected: type[Exception],
    ) -> None:
        class _Refreshable:
            def get_frozen_credentials(self) -> Credentials:
                raise ClientError(
                    {"Error": {"Code": code, "Message": "no"}},
                    "AssumeRoleWithWebIdentity",
                )

        class _Session:
            def get_credentials(self) -> _Refreshable:
                return _Refreshable()

        monkeypatch.setattr(
            "unique_search_proxy_client.web.core.search_engines.aws.service.get_session",
            _Session,
        )
        with pytest.raises(expected):
            resolve_aws_credentials()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_credentials_are_resolved_off_the_event_loop(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        threads: list[threading.Thread] = []

        def resolve() -> Credentials:
            threads.append(threading.current_thread())
            return _credentials()

        monkeypatch.setattr(
            "unique_search_proxy_client.web.core.search_engines.aws.service.resolve_aws_credentials",
            resolve,
        )
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"results": [{"url": "https://www.snb.ch/", "title": "SNB"}]},
            ),
        )
        async with httpx.AsyncClient(transport=transport) as client:
            await AwsSearchService(http_client=client).search(_request())

        assert threads
        assert threads[0] is not threading.main_thread()
        # A dedicated thread, not the shared default executor.
        assert threads[0].name.startswith("aws-credentials")

    @pytest.mark.ai
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "endpoint",
        [
            "https://search.example.com",
            "http://bedrock-agentcore.us-east-1.amazonaws.com",
            "https://amazonaws.com.example.com",
            "https://user:pw@bedrock-agentcore.us-east-1.amazonaws.com",
            "https://abc123.execute-api.us-east-1.amazonaws.com",
            "https://bedrock-agentcore.us-east-1.amazonaws.com.evil.example",
            "https://evil-bedrock-agentcore.us-east-1.amazonaws.com",
            "https://bucket.s3.us-east-1.amazonaws.com",
        ],
    )
    async def test_non_aws_endpoint_is_refused_before_signing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        aws_env: None,
        endpoint: str,
    ) -> None:
        monkeypatch.setattr(
            service,
            "credentials",
            service.credentials.model_copy(update={"api_endpoint": endpoint}),
        )
        sent: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            sent.append(request)
            return httpx.Response(200, json={"results": []})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(EngineNotConfiguredError):
                await AwsSearchService(http_client=client).search(_request())
        assert sent == []

    @pytest.mark.ai
    @pytest.mark.parametrize(
        "endpoint",
        [
            "https://bedrock-agentcore.eu-west-1.amazonaws.com",
            "https://vpce-0abc-xyz.bedrock-agentcore.eu-west-1.vpce.amazonaws.com/",
            "https://vpce-0abc-xyz-eu-west-1a.bedrock-agentcore.eu-west-1.vpce.amazonaws.com",
            "https://bedrock-agentcore-fips.us-east-1.amazonaws.com",
        ],
    )
    def test_aws_endpoints_are_accepted(self, endpoint: str) -> None:
        assert service._invoke_url(endpoint).endswith(
            "/web-search/web-search.v1/invoke"
        )

    @pytest.mark.ai
    def test_session_is_reused_across_requests(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        created: list[object] = []

        class _Session:
            def __init__(self) -> None:
                created.append(self)

            def get_credentials(self) -> Credentials:
                return _credentials()

        monkeypatch.setattr(
            "unique_search_proxy_client.web.core.search_engines.aws.service.get_session",
            _Session,
        )
        resolve_aws_credentials()
        resolve_aws_credentials()
        assert len(created) == 1

    @pytest.mark.ai
    def test_missing_credentials_are_looked_up_again(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        found: list[Credentials | None] = [None, _credentials()]

        class _Session:
            def get_credentials(self) -> Credentials | None:
                return found.pop(0)

        monkeypatch.setattr(
            "unique_search_proxy_client.web.core.search_engines.aws.service.get_session",
            _Session,
        )
        with pytest.raises(EngineNotConfiguredError):
            resolve_aws_credentials()
        assert resolve_aws_credentials().access_key == "AKIDEXAMPLE"

    @pytest.mark.ai
    def test_null_domain_lists_from_the_admin_form_become_empty(self) -> None:
        config = AwsConfig.model_validate(
            {"include_domains": None, "exclude_domains": None},
        )
        assert config.include_domains == []
        assert config.exclude_domains == []
        schema = AwsConfig.model_json_schema()
        assert schema["properties"]["includeDomains"]["type"] == ["array", "null"]

    @pytest.mark.ai
    def test_fetch_size_above_25_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            AwsConfig(fetch_size=26)

    @pytest.mark.ai
    def test_domain_entries_become_bare_domains(self) -> None:
        entries = ["https://WWW.snb.ch/en/", " ", "nasa.gov.", "snb.ch/about"]
        expected = ["www.snb.ch", "nasa.gov", "snb.ch"]
        assert AwsConfig(include_domains=entries).include_domains == expected
        request = AwsSearchRequest.model_validate(
            {"query": "q", "includeDomains": entries, "excludeDomains": None}
        )
        assert request.include_domains == expected
        assert request.exclude_domains == []

    @pytest.mark.ai
    def test_entry_that_is_not_a_domain_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="not a domain"):
            AwsSearchRequest.model_validate(
                {"query": "q", "excludeDomains": ["not a domain"]}
            )

    @pytest.mark.ai
    def test_reversed_published_range_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="publishedAfter"):
            AwsSearchRequest.model_validate(
                {
                    "query": "q",
                    "publishedAfter": "2026-11-16T00:00:00Z",
                    "publishedBefore": "2026-11-15T00:00:00Z",
                }
            )
        with pytest.raises(ValueError, match="publishedAfter"):
            AwsConfig.model_validate(
                {
                    "publishedAfter": {"expose": True, "value": "2026-11-16T00:00:00"},
                    "publishedBefore": {
                        "expose": True,
                        "value": "2026-11-15T00:00:00Z",
                    },
                }
            )

    @pytest.mark.ai
    def test_equal_and_single_published_bounds_are_valid(self) -> None:
        same = "2026-11-15T00:00:00Z"
        AwsSearchRequest.model_validate(
            {"query": "q", "publishedAfter": same, "publishedBefore": same}
        )
        AwsSearchRequest.model_validate({"query": "q", "publishedAfter": same})
