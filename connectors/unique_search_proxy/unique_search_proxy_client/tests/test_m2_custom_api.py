from __future__ import annotations

import json
import socket
from typing import Any

import httpx
import pytest
import unique_search_proxy_core.url_safety.dns as url_safety_dns
from unique_search_proxy_core.errors import ForbiddenTargetError
from unique_search_proxy_core.search_engines.custom_api.schema import (
    CustomApiRequestMethod,
    CustomApiSearchRequest,
)

import unique_search_proxy_client.web.core.search_engines.custom_api.service as custom_api_service_module
from unique_search_proxy_client.web.core.search_engines.custom_api.service import (
    CustomApiSearchService,
)


def _custom_api_request(**fields: Any) -> CustomApiSearchRequest:
    return CustomApiSearchRequest.model_validate(
        {
            "query": "hello",
            "apiEndpoint": "https://api.example.com/search",
            **fields,
        },
    )


class TestCustomApiSearchService:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__pins_get_request_and_maps_results(self) -> None:
        """
        Purpose: Verify Custom API GET requests use pinned egress and map results.
        Why this matters: Tenant endpoints must not create a DNS-rebinding window.
        Setup summary: Resolve a public host, capture the request, and assert pinning.
        """
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "url": "https://result.example.com",
                            "title": "Result",
                            "snippet": "Snippet",
                        }
                    ]
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = CustomApiSearchService(http_client=client)
            _raw, curated = await service.search(
                _custom_api_request(
                    apiAdditionalQueryParams='{"language": "en"}',
                ),
            )

        assert len(captured) == 1
        request = captured[0]
        assert str(request.url).startswith(
            "https://93.184.216.34/search?language=en&query=hello"
        )
        assert request.headers["Host"] == "api.example.com"
        assert request.extensions["sni_hostname"] == "api.example.com"
        assert curated.results[0].url == "https://result.example.com"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__builds_post_body(self) -> None:
        """
        Purpose: Verify Custom API POST requests merge the search query into JSON.
        Why this matters: Proxy routing must preserve the legacy Custom API contract.
        Setup summary: Capture one POST and inspect its query params and JSON body.
        """
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"results": []})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = CustomApiSearchService(http_client=client)
            await service.search(
                _custom_api_request(
                    apiRequestMethod=CustomApiRequestMethod.POST,
                    apiAdditionalQueryParams='{"version": "v2"}',
                    apiAdditionalBodyParams='{"limit": 5}',
                ),
            )

        request = captured[0]
        assert request.method == "POST"
        assert request.url.params["version"] == "v2"
        assert json.loads(request.content) == {"limit": 5, "query": "hello"}

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__blocks_private_endpoint_before_request(self) -> None:
        """
        Purpose: Verify private Custom API endpoints are rejected before egress.
        Why this matters: Tenant configuration must not enable server-side requests.
        Setup summary: Configure localhost, expect a policy error, and assert no call.
        """
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"results": []})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = CustomApiSearchService(http_client=client)
            with pytest.raises(ForbiddenTargetError, match="blocked"):
                await service.search(
                    _custom_api_request(
                        apiEndpoint="http://127.0.0.1:8080/private",
                    ),
                )

        assert captured == []

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__allows_configured_custom_api_private_host(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def fake_getaddrinfo(*args: object, **kwargs: object) -> list[tuple]:
            return [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    6,
                    "",
                    ("10.20.30.40", 443),
                )
            ]

        monkeypatch.setattr(url_safety_dns.socket, "getaddrinfo", fake_getaddrinfo)
        monkeypatch.setattr(
            custom_api_service_module,
            "url_safety_settings",
            custom_api_service_module.url_safety_settings.model_copy(
                update={
                    "custom_api_trusted_private_hosts": ["search.private.example"],
                },
            ),
        )
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"results": []})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = CustomApiSearchService(http_client=client)
            await service.search(
                _custom_api_request(
                    apiEndpoint="https://search.private.example/query",
                ),
            )

        assert str(captured[0].url).startswith("https://10.20.30.40/query")
        assert captured[0].headers["Host"] == "search.private.example"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__rejects_redirect_without_following(self) -> None:
        """
        Purpose: Verify Custom API redirects are rejected and never followed.
        Why this matters: A public endpoint must not redirect proxy egress internally.
        Setup summary: Return a metadata redirect and assert only one request occurs.
        """
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(
                302,
                headers={
                    "location": "http://169.254.169.254/latest/meta-data",
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = CustomApiSearchService(http_client=client)
            with pytest.raises(ForbiddenTargetError, match="redirects are not allowed"):
                await service.search(_custom_api_request())

        assert len(captured) == 1

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__accepts_legacy_curated_response_alias(self) -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(
                    200,
                    json={
                        "curated": [
                            {
                                "url": "https://result.example.com",
                                "title": "Result",
                                "snippet": "Snippet",
                            }
                        ]
                    },
                ),
            ),
        ) as client:
            service = CustomApiSearchService(http_client=client)
            _raw, curated = await service.search(_custom_api_request())

        assert curated.results[0].url == "https://result.example.com"
