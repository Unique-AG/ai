from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_search_proxy_core.context import RequestContext
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
        request_context = RequestContext(
            company_id="company-1",
            user_id="user-1",
            chat_id="chat-1",
        )
        search = GoogleSearch(config, request_context=request_context)

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

        mock_open_client.assert_called_once_with(
            timeout=30.0,
            context=request_context,
        )
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

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("extra_fields", "expected_snippet"),
        [
            pytest.param(
                {
                    "pagemap": {
                        "metatags": [
                            {
                                "og:description": "Head of Research at Example AG &amp; author.\n\nZurich"
                            }
                        ]
                    }
                },
                "Short excerpt ...\nHead of Research at Example AG & author. Zurich",
                id="og-description-appended",
            ),
            pytest.param(
                {
                    "pagemap": {
                        "metatags": [
                            {"twitter:description": "Twitter-only description."}
                        ]
                    }
                },
                "Short excerpt ...\nTwitter-only description.",
                id="twitter-fallback",
            ),
            pytest.param(
                {"pagemap": {"metatags": [{"og:description": "Short excerpt"}]}},
                "Short excerpt ...",
                id="repeats-snippet",
            ),
            pytest.param(
                {"pagemap": {"metatags": [{"og:description": "None."}]}},
                "Short excerpt ...",
                id="placeholder",
            ),
            pytest.param({}, "Short excerpt ...", id="no-pagemap"),
        ],
    )
    def test_extract_urls__adds_page_description_to_snippet__like_search_proxy(
        self, extra_fields, expected_snippet
    ):
        """
        Purpose: The legacy (direct Google) path builds the same snippet as the proxy:
            snippet, then the page's own description unless it adds nothing.
        Why this matters: Tenants without proxy routing should get the same search
            text as proxy tenants, especially for pages that can't be crawled.
        Setup summary: Mock Google response with one item per case; assert the snippet.
        """
        item = {
            "link": "https://example.com/a",
            "title": "Example",
            "snippet": "Short excerpt ...",
            **extra_fields,
        }
        response = Mock()
        response.json.return_value = {"items": [item]}

        results = GoogleSearch(GoogleConfig())._extract_urls(response)

        assert results == [
            WebSearchResult(
                url="https://example.com/a", title="Example", snippet=expected_snippet
            )
        ]
