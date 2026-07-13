from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_search_proxy_core.param_policy.exposable_param import ExposableParam
from unique_search_proxy_core.search_engines.google.schema import (
    ExposableStrOrNone,
    GoogleConfig,
)

from unique_web_search.services.search_engine.google import GoogleSearch
from unique_web_search.services.search_engine.schema import WebSearchResult


class TestGoogleSearch:
    @pytest.mark.asyncio
    async def test_proxy_search_passes_merged_config_to_client(self):
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
            mock_client.search.search = mock_search
            mock_open_client.return_value.__aenter__.return_value = mock_client

            results = await search.search("test query")

        mock_search.assert_awaited_once()
        call_kwargs = mock_search.await_args.kwargs
        assert call_kwargs["query"] == "test query"
        assert call_kwargs["engine"] == "google"
        assert call_kwargs["fetch_size"] == 3
        assert call_kwargs["search_engine_id"] == "cx-123"
        assert call_kwargs["gl"] == "us"
        assert call_kwargs["site_search"] == "example.com"
        assert "date_restrict" not in call_kwargs
        assert results == [
            WebSearchResult(
                url="https://example.com/page",
                title="Hit",
                snippet="Details",
            )
        ]

    def test_legacy_request_params_merge_config_and_call_overrides(self):
        config = GoogleConfig(
            safe="off",
            gl=ExposableParam(expose=False, value="de"),
            date_restrict=ExposableStrOrNone(expose=True, value="m1"),
        )
        search = GoogleSearch(config)
        Exposed = config.exposed_params_model()
        assert Exposed is not None
        call_params = Exposed(dateRestrict="d7")

        mock_settings = Mock(
            is_configured=True,
            search_engine_id="cx-legacy",
            api_key="key-legacy",
            api_endpoint="https://example.test/customsearch",
        )
        with patch(
            "unique_web_search.services.search_engine.google.get_google_search_settings",
            return_value=mock_settings,
        ):
            request = search._get_request_params(
                query="ai news",
                params=call_params,
                start_index=1,
                num_fetch=5,
            )

        assert request["url"] == "https://example.test/customsearch"
        assert request["params"] == {
            "q": "ai news",
            "cx": "cx-legacy",
            "key": "key-legacy",
            "start": 1,
            "num": 5,
            "safe": "off",
            "gl": "de",
            "dateRestrict": "d7",
        }

    def test_legacy_request_params_use_config_defaults_without_call_params(self):
        config = GoogleConfig(
            safe="off",
            gl=ExposableParam(expose=False, value="de"),
            date_restrict=ExposableParam(expose=False, value="m1"),
        )
        search = GoogleSearch(config)

        mock_settings = Mock(
            is_configured=True,
            search_engine_id="cx-legacy",
            api_key="key-legacy",
            api_endpoint="https://example.test/customsearch",
        )
        with patch(
            "unique_web_search.services.search_engine.google.get_google_search_settings",
            return_value=mock_settings,
        ):
            request = search._get_request_params(
                query="ai news",
                params=None,
                start_index=11,
                num_fetch=10,
            )

        assert request["params"] == {
            "q": "ai news",
            "cx": "cx-legacy",
            "key": "key-legacy",
            "start": 11,
            "num": 10,
            "safe": "off",
            "gl": "de",
            "dateRestrict": "m1",
        }
