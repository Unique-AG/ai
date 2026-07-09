from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_search_proxy_core.param_policy.exposable_param import ExposableParam
from unique_search_proxy_core.search_engines.google.schema import GoogleConfig

from unique_web_search.services.search_engine.google import GoogleSearch
from unique_web_search.services.search_engine.schema import WebSearchResult


class TestGoogleSearch:
    @pytest.mark.asyncio
    async def test_proxy_search_merges_config_and_invocation(self):
        config = GoogleConfig(
            fetch_size=3,
            search_engine_id="cx-123",
            gl=ExposableParam(expose=False, value="us"),
            site_search=ExposableParam(expose=False, value="example.com"),
        )
        search = GoogleSearch(config)

        mock_response = Mock()
        mock_response.curated = [
            Mock(
                url="https://example.com/page",
                title="Hit",
                snippet="Details",
                content="",
            )
        ]
        mock_search = AsyncMock(return_value=mock_response)

        with (
            patch(
                "unique_web_search.services.search_engine.base.search_proxy_client_enabled",
                True,
            ),
            patch(
                "unique_web_search.services.search_engine.base.open_search_proxy_client"
            ) as mock_open_client,
        ):
            mock_client = AsyncMock()
            mock_client.search = Mock()
            mock_client.search.search = mock_search
            mock_open_client.return_value.__aenter__.return_value = mock_client

            results = await search.search("test query", params={"gl": "ch"})

        mock_search.assert_awaited_once()
        assert mock_search.await_args.kwargs == {
            "query": "test query",
            "engine": "google",
            "fetch_size": 3,
            "timeout": 30,
            "search_engine_id": "cx-123",
            "safe": "active",
            "gl": "ch",
            "site_search": "example.com",
        }
        assert results == [
            WebSearchResult(
                url="https://example.com/page",
                title="Hit",
                snippet="Details",
            )
        ]

    def test_legacy_additional_params_built_from_flat_fields(self):
        config = GoogleConfig(
            safe="off",
            gl=ExposableParam(expose=False, value="de"),
            date_restrict=ExposableParam(expose=False, value="m1"),
        )
        search = GoogleSearch(config)

        assert search._additional_params == {
            "safe": "off",
            "gl": "de",
            "dateRestrict": "m1",
        }
