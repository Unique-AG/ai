from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import Response

from unique_web_search.services.search_engine.base import SearchEngineType
from unique_web_search.services.search_engine.brave import (
    HEADERS,
    PAGINATION_SIZE,
    BraveSearch,
    BraveSearchConfig,
    BraveSearchParameters,
    get_headers,
)
from unique_web_search.services.search_engine.schema import WebSearchResult


class TestGetHeaders:
    def test_returns_subscription_token_header(self):
        headers = get_headers("my-api-key")
        assert headers["X-Subscription-Token"] == "my-api-key"

    def test_preserves_base_headers(self):
        headers = get_headers("key")
        assert headers["Accept"] == "application/json"
        assert headers["Accept-Encoding"] == "gzip"

    def test_does_not_mutate_global_headers(self):
        get_headers("key")
        assert "X-Subscription-Token" not in HEADERS


class TestBraveSearchParameters:
    def test_defaults(self):
        params = BraveSearchParameters(q="test", count=10, offset=0)
        assert params.safesearch == "strict"
        assert params.extra_snippets is True

    def test_extra_snippets_can_be_disabled(self):
        params = BraveSearchParameters(
            q="test", count=10, offset=0, extra_snippets=False
        )
        assert params.extra_snippets is False

    def test_model_dump_includes_extra_snippets(self):
        params = BraveSearchParameters(q="query", count=5, offset=0)
        dumped = params.model_dump()
        assert "extra_snippets" in dumped
        assert dumped["extra_snippets"] is True


class TestBraveSearchConfig:
    def test_default_requires_scraping_is_false(self):
        config = BraveSearchConfig(search_engine_name=SearchEngineType.BRAVE)
        assert config.requires_scraping is False

    def test_requires_scraping_can_be_enabled(self):
        config = BraveSearchConfig(
            search_engine_name=SearchEngineType.BRAVE, requires_scraping=True
        )
        assert config.requires_scraping is True

    def test_default_search_engine_name(self):
        config = BraveSearchConfig()
        assert config.search_engine_name == SearchEngineType.BRAVE

    def test_default_fetch_size(self):
        config = BraveSearchConfig()
        assert config.fetch_size == 5

    def test_custom_fetch_size(self):
        config = BraveSearchConfig(fetch_size=30)
        assert config.fetch_size == 30

    def test_model_config_title(self):
        config = BraveSearchConfig()
        assert config.model_config.get("title") == "Brave Search Engine"


@pytest.fixture
def _mock_brave_settings():
    settings = Mock()
    settings.is_configured = True
    settings.api_key = "test-key"
    settings.api_endpoint = "https://api.search.brave.com/res/v1/web/search"
    with patch(
        "unique_web_search.services.search_engine.brave.get_brave_search_settings",
        return_value=settings,
    ):
        yield settings


class TestBraveSearchInit:
    def test_is_configured_from_settings(self, _mock_brave_settings):
        config = BraveSearchConfig()
        search = BraveSearch(config)
        assert search.is_configured is True

    def test_requires_scraping_delegates_to_config(self, _mock_brave_settings):
        config_no = BraveSearchConfig(requires_scraping=False)
        config_yes = BraveSearchConfig(requires_scraping=True)

        assert BraveSearch(config_no).requires_scraping is False
        assert BraveSearch(config_yes).requires_scraping is True


class TestBraveSearchExtractUrls:
    def _make_search(self, mock_settings):
        return BraveSearch(BraveSearchConfig())

    def test_extracts_web_results(self, _mock_brave_settings):
        search = self._make_search(_mock_brave_settings)
        response = {
            "web": {
                "results": [
                    {
                        "url": "https://example.com",
                        "title": "Example",
                        "description": "A description",
                    }
                ]
            }
        }

        results = search._extract_urls(response)

        assert len(results) == 1
        assert results[0].url == "https://example.com"
        assert results[0].title == "Example"
        assert results[0].snippet == "A description"

    def test_extracts_news_results(self, _mock_brave_settings):
        search = self._make_search(_mock_brave_settings)
        response = {
            "news": {
                "results": [
                    {
                        "url": "https://news.example.com",
                        "title": "News",
                        "description": "News desc",
                    }
                ]
            }
        }

        results = search._extract_urls(response)

        assert len(results) == 1
        assert results[0].url == "https://news.example.com"

    def test_merges_web_and_news_results(self, _mock_brave_settings):
        search = self._make_search(_mock_brave_settings)
        response = {
            "web": {
                "results": [
                    {
                        "url": "https://web.example.com",
                        "title": "Web",
                        "description": "Web desc",
                    }
                ]
            },
            "news": {
                "results": [
                    {
                        "url": "https://news.example.com",
                        "title": "News",
                        "description": "News desc",
                    }
                ]
            },
        }

        results = search._extract_urls(response)

        assert len(results) == 2
        urls = [r.url for r in results]
        assert "https://web.example.com" in urls
        assert "https://news.example.com" in urls

    def test_returns_empty_list_when_no_results(self, _mock_brave_settings):
        search = self._make_search(_mock_brave_settings)
        assert search._extract_urls({}) == []

    def test_returns_empty_list_when_web_is_none(self, _mock_brave_settings):
        search = self._make_search(_mock_brave_settings)
        assert search._extract_urls({"web": None}) == []

    def test_returns_empty_list_when_news_is_none(self, _mock_brave_settings):
        search = self._make_search(_mock_brave_settings)
        assert search._extract_urls({"news": None}) == []

    def test_snippet_defaults_to_no_snippet_found(self, _mock_brave_settings):
        search = self._make_search(_mock_brave_settings)
        response = {
            "web": {
                "results": [
                    {
                        "url": "https://example.com",
                        "title": "No Desc",
                    }
                ]
            }
        }

        results = search._extract_urls(response)

        assert results[0].snippet == "No Snippet Found"

    def test_extra_snippets_joined_as_content(self, _mock_brave_settings):
        search = self._make_search(_mock_brave_settings)
        response = {
            "web": {
                "results": [
                    {
                        "url": "https://example.com",
                        "title": "Extra",
                        "description": "desc",
                        "extra_snippets": ["snippet one", "snippet two"],
                    }
                ]
            }
        }

        results = search._extract_urls(response)

        assert results[0].content == "snippet one\nsnippet two"

    def test_content_empty_when_no_extra_snippets(self, _mock_brave_settings):
        search = self._make_search(_mock_brave_settings)
        response = {
            "web": {
                "results": [
                    {
                        "url": "https://example.com",
                        "title": "No Extra",
                        "description": "desc",
                    }
                ]
            }
        }

        results = search._extract_urls(response)

        assert results[0].content == ""

    def test_returns_web_search_result_instances(self, _mock_brave_settings):
        search = self._make_search(_mock_brave_settings)
        response = {
            "web": {
                "results": [
                    {
                        "url": "https://example.com",
                        "title": "T",
                        "description": "D",
                    }
                ]
            }
        }

        results = search._extract_urls(response)

        assert all(isinstance(r, WebSearchResult) for r in results)


class TestBraveSearchPagination:
    @pytest.mark.asyncio
    async def test_single_page_fetch(self, _mock_brave_settings):
        config = BraveSearchConfig(fetch_size=5)
        search = BraveSearch(config)

        mock_response = Mock(spec=Response)
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {
                        "url": f"https://example.com/{i}",
                        "title": f"T{i}",
                        "description": f"D{i}",
                    }
                    for i in range(PAGINATION_SIZE)
                ]
            }
        }

        with patch.object(
            search,
            "_perform_web_search_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_req:
            results = await search.search("test")

            assert mock_req.call_count == 1
            params = mock_req.call_args[1]["params"]
            assert params.count == PAGINATION_SIZE
            assert params.offset == 0

        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_multi_page_fetch(self, _mock_brave_settings):
        config = BraveSearchConfig(fetch_size=25)
        search = BraveSearch(config)

        def make_response(count):
            mock_resp = Mock(spec=Response)
            mock_resp.json.return_value = {
                "web": {
                    "results": [
                        {
                            "url": f"https://example.com/{i}",
                            "title": f"T{i}",
                            "description": f"D{i}",
                        }
                        for i in range(count)
                    ]
                }
            }
            return mock_resp

        responses = [make_response(PAGINATION_SIZE), make_response(PAGINATION_SIZE)]
        with patch.object(
            search,
            "_perform_web_search_request",
            new_callable=AsyncMock,
            side_effect=responses,
        ) as mock_req:
            results = await search.search("test")

            assert mock_req.call_count == 2
            first_params = mock_req.call_args_list[0][1]["params"]
            assert first_params.count == PAGINATION_SIZE
            assert first_params.offset == 0

            second_params = mock_req.call_args_list[1][1]["params"]
            assert second_params.count == PAGINATION_SIZE
            assert second_params.offset == 1

        assert len(results) == 25

    @pytest.mark.asyncio
    async def test_exact_page_boundary_fetch(self, _mock_brave_settings):
        config = BraveSearchConfig(fetch_size=20)
        search = BraveSearch(config)

        mock_response = Mock(spec=Response)
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {
                        "url": f"https://example.com/{i}",
                        "title": f"T{i}",
                        "description": f"D{i}",
                    }
                    for i in range(20)
                ]
            }
        }

        with patch.object(
            search,
            "_perform_web_search_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_req:
            results = await search.search("test")
            assert mock_req.call_count == 1

        assert len(results) == 20

    @pytest.mark.asyncio
    async def test_three_page_fetch(self, _mock_brave_settings):
        config = BraveSearchConfig(fetch_size=50)
        search = BraveSearch(config)

        def make_response(count):
            mock_resp = Mock(spec=Response)
            mock_resp.json.return_value = {
                "web": {
                    "results": [
                        {
                            "url": f"https://example.com/{i}",
                            "title": f"T{i}",
                            "description": f"D{i}",
                        }
                        for i in range(count)
                    ]
                }
            }
            return mock_resp

        responses = [
            make_response(PAGINATION_SIZE),
            make_response(PAGINATION_SIZE),
            make_response(PAGINATION_SIZE),
        ]
        with patch.object(
            search,
            "_perform_web_search_request",
            new_callable=AsyncMock,
            side_effect=responses,
        ) as mock_req:
            results = await search.search("test")

            assert mock_req.call_count == 3

            offsets = [call[1]["params"].offset for call in mock_req.call_args_list]
            assert offsets == [0, 1, 2]

            counts = [call[1]["params"].count for call in mock_req.call_args_list]
            assert counts == [PAGINATION_SIZE, PAGINATION_SIZE, PAGINATION_SIZE]

        assert len(results) == 50

    @pytest.mark.asyncio
    async def test_query_passed_to_params(self, _mock_brave_settings):
        config = BraveSearchConfig(fetch_size=5)
        search = BraveSearch(config)

        mock_response = Mock(spec=Response)
        mock_response.json.return_value = {"web": {"results": []}}

        with patch.object(
            search,
            "_perform_web_search_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_req:
            await search.search("my search query")
            params = mock_req.call_args[1]["params"]
            assert params.q == "my search query"
            assert params.count == PAGINATION_SIZE


class TestBraveSearchPerformRequest:
    @pytest.mark.asyncio
    async def test_uses_correct_api_endpoint_and_headers(self, _mock_brave_settings):
        config = BraveSearchConfig(fetch_size=5)
        search = BraveSearch(config)
        params = BraveSearchParameters(q="test", count=5, offset=0)

        mock_response = Mock(spec=Response)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch(
            "unique_web_search.services.search_engine.brave.AsyncClient"
        ) as MockAsyncClient:
            MockAsyncClient.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            MockAsyncClient.return_value.__aexit__ = AsyncMock(return_value=None)

            response = await search._perform_web_search_request(params=params)

            mock_client.get.assert_called_once()
            call_kwargs = mock_client.get.call_args[1]
            assert call_kwargs["headers"]["X-Subscription-Token"] == "test-key"
            assert "X-Subscription-Key" not in call_kwargs["headers"]

        assert response is mock_response

    @pytest.mark.asyncio
    async def test_passes_params_as_model_dump(self, _mock_brave_settings):
        config = BraveSearchConfig(fetch_size=5)
        search = BraveSearch(config)
        params = BraveSearchParameters(q="hello", count=10, offset=1)

        mock_response = Mock(spec=Response)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch(
            "unique_web_search.services.search_engine.brave.AsyncClient"
        ) as MockAsyncClient:
            MockAsyncClient.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            MockAsyncClient.return_value.__aexit__ = AsyncMock(return_value=None)

            await search._perform_web_search_request(params=params)

            call_kwargs = mock_client.get.call_args[1]
            assert call_kwargs["params"] == params.model_dump(exclude_none=True)
