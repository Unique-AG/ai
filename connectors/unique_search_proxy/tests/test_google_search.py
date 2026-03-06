from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from core.google_search.exceptions import (
    GoogleSearchAPIEndpointNotSetException,
    GoogleSearchAPIKeyNotSetException,
    GoogleSearchEngineIDNotSetException,
)
from core.google_search.search import (
    GoogleSearch,
    GoogleSearchParams,
    _map_google_search_response_to_web_search_result,
)
from httpx import Response


class TestMapGoogleSearchResponse:
    def test_maps_items(self):
        response = MagicMock(spec=Response)
        response.json.return_value = {
            "items": [
                {"link": "https://a.com", "title": "A", "snippet": "Snip A"},
                {"link": "https://b.com", "title": "B", "snippet": "Snip B"},
            ]
        }
        results = _map_google_search_response_to_web_search_result(response)
        assert len(results) == 2
        assert results[0].url == "https://a.com"
        assert results[0].title == "A"
        assert results[0].snippet == "Snip A"
        assert results[1].url == "https://b.com"

    def test_empty_items(self):
        response = MagicMock(spec=Response)
        response.json.return_value = {"items": []}
        results = _map_google_search_response_to_web_search_result(response)
        assert results == []

    def test_no_items_key(self):
        response = MagicMock(spec=Response)
        response.json.return_value = {}
        results = _map_google_search_response_to_web_search_result(response)
        assert results == []

    def test_missing_fields_use_defaults(self):
        response = MagicMock(spec=Response)
        response.json.return_value = {"items": [{}]}
        results = _map_google_search_response_to_web_search_result(response)
        assert len(results) == 1
        assert results[0].url == "URL not available"
        assert results[0].title == "Title not available"
        assert results[0].snippet == "Snippet not available"

    def test_html_title_fallback(self):
        response = MagicMock(spec=Response)
        response.json.return_value = {
            "items": [{"link": "u", "htmlTitle": "HTML Title", "snippet": "s"}]
        }
        results = _map_google_search_response_to_web_search_result(response)
        assert results[0].title == "HTML Title"


class TestGoogleSearchInit:
    def test_init_with_env(self, google_search_env):
        params = GoogleSearchParams()
        gs = GoogleSearch(params)
        assert gs.api_key == "test-api-key"
        assert gs.api_endpoint == "https://example.com/search"
        assert gs.engine_id == "test-engine-id"
        assert gs.fetch_size == 10

    def test_init_cx_override(self, google_search_env):
        params = GoogleSearchParams(cx="override-cx")
        gs = GoogleSearch(params)
        assert gs.engine_id == "override-cx"

    def test_missing_api_key(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_SEARCH_API_ENDPOINT", "https://x.com")
        monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "cx")
        monkeypatch.delenv("GOOGLE_SEARCH_API_KEY", raising=False)
        with pytest.raises(GoogleSearchAPIKeyNotSetException):
            GoogleSearch(GoogleSearchParams())

    def test_missing_api_endpoint(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "key")
        monkeypatch.delenv("GOOGLE_SEARCH_API_ENDPOINT", raising=False)
        monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "cx")
        with pytest.raises(GoogleSearchAPIEndpointNotSetException):
            GoogleSearch(GoogleSearchParams())

    def test_missing_engine_id(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "key")
        monkeypatch.setenv("GOOGLE_SEARCH_API_ENDPOINT", "https://x.com")
        monkeypatch.delenv("GOOGLE_SEARCH_ENGINE_ID", raising=False)
        with pytest.raises(GoogleSearchEngineIDNotSetException):
            GoogleSearch(GoogleSearchParams())


class TestGoogleSearchSearch:
    async def test_search_returns_results(self, google_search_env):
        params = GoogleSearchParams.model_validate({"fetchSize": 5})
        gs = GoogleSearch(params)

        mock_response = MagicMock(spec=Response)
        mock_response.json.return_value = {
            "items": [
                {"link": "https://r.com", "title": "R", "snippet": "Result"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("core.google_search.search.AsyncClient", return_value=mock_client):
            results = await gs.search("test query")

        assert len(results) == 1
        assert results[0].url == "https://r.com"

    async def test_search_pagination(self, google_search_env):
        params = GoogleSearchParams.model_validate({"fetchSize": 15})
        gs = GoogleSearch(params)

        mock_response = MagicMock(spec=Response)
        mock_response.json.return_value = {
            "items": [{"link": "u", "title": "t", "snippet": "s"}]
        }
        mock_response.raise_for_status = MagicMock()

        call_count = 0

        class FakeClient:
            async def get(self, url, params=None):
                nonlocal call_count
                call_count += 1
                return mock_response

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        with patch("core.google_search.search.AsyncClient", return_value=FakeClient()):
            await gs.search("query")

        assert call_count == 2
