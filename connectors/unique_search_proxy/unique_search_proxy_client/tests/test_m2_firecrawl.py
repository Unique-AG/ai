from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from unique_search_proxy_core.errors import (
    EmptySearchResultsError,
    EngineNotConfiguredError,
    RateLimitedError,
    UpstreamError,
    UpstreamTimeoutError,
)
from unique_search_proxy_core.schema import ProxyErrorCode, WebSearchResults
from unique_search_proxy_core.search_engines.firecrawl.schema import (
    FirecrawlSearchRequest,
)

from unique_search_proxy_client.web.app import create_app
from unique_search_proxy_client.web.core.search_engines.firecrawl.service import (
    FirecrawlSearchService,
)

_SERVICE_CREDENTIALS = (
    "unique_search_proxy_client.web.core.search_engines.firecrawl.service.credentials"
)


def _web_item(
    *,
    url: str = "https://example.com/page",
    markdown: str | None = "# Example page",
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "url": url,
        "title": "Example",
        "description": "An example description",
    }
    if markdown is not None:
        item["markdown"] = markdown
    return item


def _firecrawl_payload(**data: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "success": True,
        "data": data or {"web": [_web_item()]},
        "creditsUsed": 3,
    }


def _use_firecrawl_credentials(
    monkeypatch: pytest.MonkeyPatch,
    *,
    zero_data_retention: str = "none",
) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setenv("FIRECRAWL_ZERO_DATA_RETENTION", zero_data_retention)
    from unique_search_proxy_client.web.settings.providers.firecrawl import (
        _get_firecrawl_crawl_credentials,
    )

    monkeypatch.setattr(_SERVICE_CREDENTIALS, _get_firecrawl_crawl_credentials())


@pytest.fixture
def firecrawl_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_firecrawl_credentials(monkeypatch)


def _firecrawl_request(**fields: Any) -> FirecrawlSearchRequest:
    return FirecrawlSearchRequest.model_validate(
        {
            "query": "hello",
            "fetch_size": 10,
            "timeout": 60,
            **fields,
        },
    )


async def _search(
    handler: Callable[[httpx.Request], httpx.Response],
    **fields: Any,
) -> WebSearchResults:
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        engine = FirecrawlSearchService(http_client=client)
        _raw, curated = await engine.search(_firecrawl_request(**fields))
    return curated


class TestFirecrawlSearchService:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__maps_scraped_page_to_content__for_web_result(
        self, firecrawl_env: None
    ) -> None:
        """
        Purpose: Verify a web result is mapped with its scraped Markdown as content.
        Why this matters: The page text is what the model reads; if it is lost,
            callers fall back to snippets or crawl the page a second time.
        Setup summary: Mock one web item with Markdown; assert url, title, snippet
            and content, and that the call is authenticated with the API key.
        """
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["auth"] = request.headers.get("Authorization")
            captured["url"] = str(request.url)
            captured["json"] = json.loads(request.content.decode())
            return httpx.Response(200, json=_firecrawl_payload())

        curated = await _search(handler)

        assert captured["auth"] == "Bearer test-key"
        assert captured["url"] == "https://api.firecrawl.dev/v2/search"
        assert captured["json"]["query"] == "hello"
        assert captured["json"]["limit"] == 10
        assert len(curated) == 1
        assert curated.results[0].url == "https://example.com/page"
        assert curated.results[0].title == "Example"
        assert curated.results[0].snippet == "An example description"
        assert curated.results[0].content == "# Example page"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__reads_news_items__when_news_source_is_requested(
        self, firecrawl_env: None
    ) -> None:
        """
        Purpose: Verify news items are returned and their text becomes the snippet.
        Why this matters: Firecrawl sends the news text as ``description`` even
            though its docs call it ``snippet``; reading one key only drops it.
        Setup summary: Mock one news item per key; assert both snippets are kept.
        """
        payload = _firecrawl_payload(
            news=[
                {
                    "url": "https://news.example.com/a",
                    "title": "A",
                    "description": "From description",
                    "snippet": None,
                },
                {
                    "url": "https://news.example.com/b",
                    "title": "B",
                    "snippet": "From snippet",
                },
            ],
        )

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        curated = await _search(handler, sources="web_and_news")

        assert [result.snippet for result in curated.results] == [
            "From description",
            "From snippet",
        ]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__returns_each_url_once__when_web_and_news_overlap(
        self, firecrawl_env: None
    ) -> None:
        """
        Purpose: Verify a URL listed under web and news is returned once.
        Why this matters: Firecrawl often returns the same article in both lists;
            duplicates waste the model's context and skew source counts.
        Setup summary: Mock the same URL in web and news; assert one result.
        """
        shared = "https://example.com/article"
        payload = _firecrawl_payload(
            web=[_web_item(url=shared)],
            news=[{"url": shared, "title": "Example", "description": "Same"}],
        )

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        curated = await _search(handler, sources="web_and_news")

        assert [result.url for result in curated.results] == [shared]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__caps_results_at_fetch_size__when_sources_return_more(
        self, firecrawl_env: None
    ) -> None:
        """
        Purpose: Verify the result count never exceeds the requested fetch size.
        Why this matters: Firecrawl applies ``limit`` to each source, so two
            sources can return twice as many results as the caller asked for.
        Setup summary: Mock two web and two news items with fetch size 3;
            assert three results, alternating web and news.
        """
        payload = _firecrawl_payload(
            web=[_web_item(url=f"https://example.com/web-{i}") for i in range(2)],
            news=[
                {"url": f"https://example.com/news-{i}", "title": "N"} for i in range(2)
            ],
        )

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        curated = await _search(handler, sources="web_and_news", fetch_size=3)

        assert [result.url for result in curated.results] == [
            "https://example.com/web-0",
            "https://example.com/news-0",
            "https://example.com/web-1",
        ]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__returns_long_previews_whole(
        self, firecrawl_env: None
    ) -> None:
        """
        Purpose: Verify a long Firecrawl preview reaches the caller uncut.
        Why this matters: Query-matched previews can hold the whole table the
            question is about. In search mode V3 that preview is all the model
            sees, so cutting it here would hide the answer. Callers that repeat
            the preview shorten it themselves.
        Setup summary: Mock one long and one short description; assert both
            come back unchanged.
        """
        long_text = "price " * 4000
        payload = _firecrawl_payload(
            web=[
                {
                    "url": "https://example.com/long",
                    "title": "L",
                    "description": long_text,
                },
                {
                    "url": "https://example.com/short",
                    "title": "S",
                    "description": "Short.",
                },
            ],
        )

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        curated = await _search(handler)
        long_snippet, short_snippet = (r.snippet for r in curated.results)

        assert long_snippet == long_text
        assert short_snippet == "Short."

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__keeps_news__when_web_fills_fetch_size(
        self, firecrawl_env: None
    ) -> None:
        """
        Purpose: Verify news results survive when web alone fills the fetch size.
        Why this matters: "Web and news" exists to bring in today's news; if a
            full web list pushed every news item out, the setting would do
            nothing while still being billed.
        Setup summary: Mock five web and five news items with fetch size 5;
            assert news items are among the results, ranked within each source.
        """
        payload = _firecrawl_payload(
            web=[_web_item(url=f"https://example.com/web-{i}") for i in range(5)],
            news=[
                {"url": f"https://example.com/news-{i}", "title": "N"} for i in range(5)
            ],
        )

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        curated = await _search(handler, sources="web_and_news", fetch_size=5)

        assert [result.url for result in curated.results] == [
            "https://example.com/web-0",
            "https://example.com/news-0",
            "https://example.com/web-1",
            "https://example.com/news-1",
            "https://example.com/web-2",
        ]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__skips_items_without_url__in_provider_response(
        self, firecrawl_env: None
    ) -> None:
        """
        Purpose: Verify items without a URL are dropped instead of failing the call.
        Why this matters: A result without a URL cannot be cited or opened, and
            one malformed item must not lose the valid ones.
        Setup summary: Mock one item without URL and one valid; assert one result.
        """
        payload = _firecrawl_payload(web=[{"title": "No url"}, _web_item()])

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        curated = await _search(handler)

        assert [result.url for result in curated.results] == [
            "https://example.com/page"
        ]

    @pytest.mark.ai
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("zero_data_retention", "expected"),
        [("none", None), ("anon", ["anon"]), ("zdr", ["zdr"])],
        ids=["none", "anon", "zdr"],
    )
    async def test_search__sends_enterprise_mode__from_deployment_setting(
        self,
        monkeypatch: pytest.MonkeyPatch,
        zero_data_retention: str,
        expected: list[str] | None,
    ) -> None:
        """
        Purpose: Verify the zero data retention mode reaches Firecrawl as ``enterprise``.
        Why this matters: A deployment that requires zero data retention must
            never send a search without it, and `none` must not send the field.
        Setup summary: Set FIRECRAWL_ZERO_DATA_RETENTION per case; assert the body.
        """
        _use_firecrawl_credentials(monkeypatch, zero_data_retention=zero_data_retention)
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["json"] = json.loads(request.content.decode())
            return httpx.Response(200, json=_firecrawl_payload())

        await _search(handler)

        assert captured["json"].get("enterprise") == expected

    @pytest.mark.ai
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("deployed", "requested", "expected"),
        [("none", "zdr", ["zdr"]), ("zdr", "anon", ["zdr"]), ("anon", "zdr", ["zdr"])],
        ids=["raises-none", "cannot-lower", "raises-anon"],
    )
    async def test_search__sends_the_stricter_enterprise_mode__of_env_and_request(
        self,
        monkeypatch: pytest.MonkeyPatch,
        deployed: str,
        requested: str,
        expected: list[str],
    ) -> None:
        """
        Purpose: Verify a search configuration can raise zero data retention
            above the deployment setting and can never lower it.
        Why this matters: One space may need end-to-end zero data retention on
            a deployment without it, but no space may weaken the operator's
            setting for the whole deployment.
        Setup summary: Set the deployment mode and the request mode per case;
            assert the `enterprise` list Firecrawl receives.
        """
        _use_firecrawl_credentials(monkeypatch, zero_data_retention=deployed)
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["json"] = json.loads(request.content.decode())
            return httpx.Response(200, json=_firecrawl_payload())

        await _search(handler, zero_data_retention=requested)

        assert captured["json"]["enterprise"] == expected

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__keeps_query_out_of_logs__on_success(
        self,
        firecrawl_env: None,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Purpose: Verify the search query is not written to the service logs.
        Why this matters: Queries can reveal what a client is researching; logs
            are kept longer and read by more people than the request itself.
        Setup summary: Search for a marker string at INFO level; assert it is
            absent from every log record.
        """

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_firecrawl_payload())

        with caplog.at_level(logging.INFO):
            await _search(handler, query="confidential-marker")

        assert "confidential-marker" not in caplog.text

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__raises_empty_results__when_provider_returns_none(
        self, firecrawl_env: None
    ) -> None:
        """
        Purpose: Verify an empty provider response raises EmptySearchResultsError.
        Why this matters: Callers distinguish "nothing found" from a failure and
            must not retry or report an outage.
        Setup summary: Mock an empty web list; assert the error.
        """

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_firecrawl_payload(web=[]))

        with pytest.raises(EmptySearchResultsError, match="no results"):
            await _search(handler)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__raises_not_configured__without_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: Verify a missing API key raises EngineNotConfiguredError.
        Why this matters: Operators need to see which variable is missing instead
            of an opaque authentication failure from Firecrawl.
        Setup summary: Set FIRECRAWL_API_KEY to NOT_PROVIDED; assert the error.
        """
        monkeypatch.setenv("FIRECRAWL_API_KEY", "NOT_PROVIDED")
        from unique_search_proxy_client.web.settings.providers.firecrawl import (
            _get_firecrawl_crawl_credentials,
        )

        monkeypatch.setattr(_SERVICE_CREDENTIALS, _get_firecrawl_crawl_credentials())

        with pytest.raises(EngineNotConfiguredError):
            await FirecrawlSearchService().search(_firecrawl_request())

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__raises_retryable_upstream_error__on_server_error(
        self, firecrawl_env: None
    ) -> None:
        """
        Purpose: Verify a Firecrawl 5xx becomes a retryable UpstreamError.
        Why this matters: A provider outage is temporary, so callers may retry.
        Setup summary: Mock an HTTP 500; assert the error and its retryable flag.
        """

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "backend"})

        with pytest.raises(UpstreamError, match="500") as exc_info:
            await _search(handler)

        assert exc_info.value.retryable is True

    @pytest.mark.ai
    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [401, 402, 403])
    async def test_search__raises_non_retryable_upstream_error__on_account_error(
        self, firecrawl_env: None, status_code: int
    ) -> None:
        """
        Purpose: Verify key, credit and feature rejections are not retryable.
        Why this matters: Firecrawl answers 403 when zero data retention is not
            enabled for the account; retrying only repeats the failure.
        Setup summary: Mock the account-level status; assert the message and flag.
        """

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code,
                json={"success": False, "error": "ZDR search is not enabled"},
            )

        with pytest.raises(UpstreamError, match="ZDR search is not enabled") as exc:
            await _search(handler)

        assert exc.value.retryable is False

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__raises_upstream_error__when_success_flag_is_false(
        self, firecrawl_env: None
    ) -> None:
        """
        Purpose: Verify an HTTP 200 with ``success: false`` is treated as a failure.
        Why this matters: Returning it as an empty result would hide a provider
            error behind "nothing found".
        Setup summary: Mock a 200 body with success false; assert the error.
        """

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"success": False, "error": "bad query"})

        with pytest.raises(UpstreamError, match="bad query"):
            await _search(handler)

    @pytest.mark.ai
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("body", "message"),
        [(b"[]", "must be a JSON object"), (b"<html>busy</html>", "invalid JSON")],
        ids=["json-array", "not-json"],
    )
    async def test_search__raises_upstream_error__when_answer_is_not_a_json_object(
        self,
        firecrawl_env: None,
        body: bytes,
        message: str,
    ) -> None:
        """
        Purpose: Verify a 200 answer that is not a JSON object becomes an
            UpstreamError.
        Why this matters: Reading it as an object raised AttributeError or a
            JSON decode error, which the route reports as an internal error
            instead of a structured upstream failure the caller can handle.
        Setup summary: Answer 200 with a JSON array and with HTML; assert the
            error type and message.
        """

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=body)

        with pytest.raises(UpstreamError, match=message):
            await _search(handler)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__drops_results_on_excluded_subdomain__of_an_included_host(
        self, firecrawl_env: None
    ) -> None:
        """
        Purpose: Verify results on an excluded subdomain are dropped when the
            parent domain is on the include list.
        Why this matters: Firecrawl rejects include and exclude lists together,
            so only the include list is sent and Firecrawl may return the
            blocked subdomain. The admin's exclusion must still hold.
        Setup summary: Include `example.com`, exclude `private.example.com`,
            return one result on each; assert the body and the kept result.
        """
        captured: dict[str, Any] = {}
        payload = _firecrawl_payload(
            web=[
                {"url": "https://private.example.com/a", "title": "Blocked"},
                {"url": "https://www.example.com/b", "title": "Allowed"},
            ],
        )

        def handler(request: httpx.Request) -> httpx.Response:
            captured["json"] = json.loads(request.content.decode())
            return httpx.Response(200, json=payload)

        curated = await _search(
            handler,
            include_domains=["example.com"],
            exclude_domains=["private.example.com"],
        )

        assert captured["json"]["includeDomains"] == ["example.com"]
        assert "excludeDomains" not in captured["json"]
        assert [result.url for result in curated.results] == [
            "https://www.example.com/b"
        ]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__raises_rate_limited__on_429(
        self, firecrawl_env: None
    ) -> None:
        """
        Purpose: Verify an HTTP 429 raises RateLimitedError with the retry delay.
        Why this matters: Callers back off for the time Firecrawl asks for.
        Setup summary: Mock a 429 with Retry-After; assert the parsed seconds.
        """

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, headers={"Retry-After": "8"})

        with pytest.raises(RateLimitedError) as exc_info:
            await _search(handler)

        assert exc_info.value.retry_after_seconds == 8

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__raises_upstream_timeout__when_request_times_out(
        self, firecrawl_env: None
    ) -> None:
        """
        Purpose: Verify a transport timeout raises UpstreamTimeoutError.
        Why this matters: Searches that also scrape pages are slow; a timeout
            must be reported as such and not as a generic failure.
        Setup summary: Raise a read timeout from the transport; assert the error.
        """

        def handler(_request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out")

        with pytest.raises(UpstreamTimeoutError):
            await _search(handler, timeout=1)


class TestFirecrawlSearchEndpoint:
    @pytest.mark.ai
    def test_search_route__returns_503__when_firecrawl_is_not_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: Verify POST /v1/search routes `firecrawl` to its service.
        Why this matters: An engine missing from the registry or factory fails
            for every caller even though the service itself works.
        Setup summary: Post a firecrawl search without an API key; assert the
            503 engine-not-configured response.
        """
        monkeypatch.setenv("FIRECRAWL_API_KEY", "NOT_PROVIDED")
        from unique_search_proxy_client.web.settings.providers.firecrawl import (
            _get_firecrawl_crawl_credentials,
        )

        monkeypatch.setattr(_SERVICE_CREDENTIALS, _get_firecrawl_crawl_credentials())

        with TestClient(create_app()) as client:
            resp = client.post(
                "/v1/search",
                json={"engine": "firecrawl", "query": "hello", "fetchSize": 3},
            )

        assert resp.status_code == 503
        assert (
            resp.json()["error"]["code"] == ProxyErrorCode.ENGINE_NOT_CONFIGURED.value
        )
