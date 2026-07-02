from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_search_proxy_core.param_policy.exposable_param import ExposableParam
from unique_search_proxy_core.search_engines.google.schema import GoogleConfig

from unique_web_search.services.search_engine.google import GoogleSearch
from unique_web_search.services.search_engine.schema import WebSearchResult


class TestGoogleSearch:
    @pytest.mark.asyncio
    async def test_proxy_search_passes_flat_config_to_client(self):
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
        mock_google = AsyncMock(return_value=mock_response)

        with (
            patch(
                "unique_web_search.services.search_engine.base.search_proxy_client_enabled",
                True,
            ),
            patch(
                "unique_web_search.services.search_engine.google.open_search_proxy_client"
            ) as mock_open_client,
        ):
            mock_client = AsyncMock()
            mock_client.search.google = mock_google
            mock_open_client.return_value.__aenter__.return_value = mock_client

            results = await search.search("test query")

        mock_google.assert_awaited_once_with(
            query="test query",
            fetch_size=3,
            search_engine_id="cx-123",
            gl="us",
            hl=None,
            lr=None,
            date_restrict=None,
            exact_terms=None,
            exclude_terms=None,
            file_type=None,
            site_search="example.com",
            site_search_filter=None,
            sort=None,
        )
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
