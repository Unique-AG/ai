from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_search_proxy_core.context import RequestContext

from unique_web_search.services.search_engine.custom_api import (
    CustomAPI,
    CustomAPIConfig,
)
from unique_web_search.services.search_engine.schema import WebSearchResult
from unique_web_search.settings import CUSTOM_API_REQUEST_METHOD


class TestCustomApiProxySearch:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__routes_full_config_through_proxy(self) -> None:
        """
        Purpose: Verify Custom API uses Search Proxy when proxy mode is enabled.
        Why this matters: Direct tool-pod egress would bypass proxy URL controls.
        Setup summary: Mock the SDK, run a search, and inspect the proxy invocation.
        """
        config = CustomAPIConfig(
            api_endpoint="https://api.example.com/search",
            api_headers='{"Authorization": "Bearer token"}',
            api_additional_query_params='{"language": "en"}',
            api_additional_body_params='{"limit": 5}',
            api_request_method=CUSTOM_API_REQUEST_METHOD.POST,
            timeout=45,
        )
        request_context = RequestContext(
            company_id="company-1",
            user_id="user-1",
            chat_id="chat-1",
        )
        search = CustomAPI(config, request_context=request_context)
        proxy_response = Mock(
            curated=[
                Mock(
                    url="https://result.example.com",
                    title="Result",
                    snippet="Snippet",
                    content="",
                )
            ],
        )
        proxy_search = AsyncMock(return_value=proxy_response)

        with (
            patch(
                "unique_web_search.services.search_engine.base.search_proxy_client_enabled",
                True,
            ),
            patch(
                "unique_web_search.services.search_engine.base.open_search_proxy_client"
            ) as open_proxy,
            patch(
                "unique_web_search.services.search_engine.custom_api.AsyncClient"
            ) as direct_client,
        ):
            proxy_client = AsyncMock()
            proxy_client.search.search = proxy_search
            open_proxy.return_value.__aenter__.return_value = proxy_client

            results = await search.search("test query")

        direct_client.assert_not_called()
        open_proxy.assert_called_once_with(timeout=30.0, context=request_context)
        proxy_search.assert_awaited_once()
        invocation = proxy_search.await_args.kwargs
        assert invocation["engine"] == "custom_api"
        assert invocation["query"] == "test query"
        assert invocation["api_endpoint"] == "https://api.example.com/search"
        assert invocation["api_headers"] == '{"Authorization": "Bearer token"}'
        assert invocation["api_additional_query_params"] == '{"language": "en"}'
        assert invocation["api_additional_body_params"] == '{"limit": 5}'
        assert invocation["api_request_method"] == "POST"
        assert invocation["timeout"] == 45
        assert "requires_scraping" not in invocation
        assert "search_engine_mode" not in invocation
        assert results == [
            WebSearchResult(
                url="https://result.example.com",
                title="Result",
                snippet="Snippet",
            )
        ]
