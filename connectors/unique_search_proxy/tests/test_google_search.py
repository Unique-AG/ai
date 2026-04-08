from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import Response

from unique_search_proxy.core.google_search.exceptions import (
    GoogleSearchAPIEndpointNotSetException,
    GoogleSearchAPIKeyNotSetException,
    GoogleSearchEngineIDNotSetException,
)
from unique_search_proxy.core.google_search.search import (
    GoogleSearch,
    GoogleSearchParams,
    _map_google_search_response_to_web_search_result,
)


class TestMapGoogleSearchResponse:
    @pytest.mark.ai
    def test_maps_items(self):
        """
        Purpose: Verify response items are mapped to WebSearchResult objects.
        Why this matters: Correct mapping is essential for returning search results to callers.
        Setup summary: Mock a response with two items and assert the mapped fields.
        """
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

    @pytest.mark.ai
    def test_empty_items(self):
        """
        Purpose: Verify an empty items list returns an empty result list.
        Why this matters: Searches may legitimately return zero results.
        Setup summary: Mock a response with empty items and assert empty output.
        """
        response = MagicMock(spec=Response)
        response.json.return_value = {"items": []}
        results = _map_google_search_response_to_web_search_result(response)
        assert results == []

    @pytest.mark.ai
    def test_no_items_key(self):
        """
        Purpose: Verify a response without an items key returns empty results.
        Why this matters: Google API may omit items entirely for zero-result queries.
        Setup summary: Mock a response with no items key and assert empty output.
        """
        response = MagicMock(spec=Response)
        response.json.return_value = {}
        results = _map_google_search_response_to_web_search_result(response)
        assert results == []

    @pytest.mark.ai
    def test_missing_fields_use_defaults(self):
        """
        Purpose: Verify missing item fields fall back to placeholder strings.
        Why this matters: Partial API responses should not crash the mapping.
        Setup summary: Mock a response with an empty item dict and assert placeholder values.
        """
        response = MagicMock(spec=Response)
        response.json.return_value = {"items": [{}]}
        results = _map_google_search_response_to_web_search_result(response)
        assert len(results) == 1
        assert results[0].url == "URL not available"
        assert results[0].title == "Title not available"
        assert results[0].snippet == "Snippet not available"

    @pytest.mark.ai
    def test_html_title_fallback(self):
        """
        Purpose: Verify htmlTitle is used when title is absent.
        Why this matters: Some Google results only provide htmlTitle.
        Setup summary: Mock a response with htmlTitle instead of title and assert fallback.
        """
        response = MagicMock(spec=Response)
        response.json.return_value = {
            "items": [{"link": "u", "htmlTitle": "HTML Title", "snippet": "s"}]
        }
        results = _map_google_search_response_to_web_search_result(response)
        assert results[0].title == "HTML Title"


class TestGoogleSearchInit:
    @pytest.mark.ai
    def test_init_with_env(self, google_search_env):
        """
        Purpose: Verify GoogleSearch reads config from environment variables.
        Why this matters: Production deployments configure search via env vars.
        Setup summary: Set env vars via fixture, construct GoogleSearch, assert fields.
        """
        params = GoogleSearchParams()
        gs = GoogleSearch(params)
        assert gs.api_key == "test-api-key"
        assert gs.api_endpoint == "https://example.com/search"
        assert gs.engine_id == "test-engine-id"
        assert gs.fetch_size == 10

    @pytest.mark.ai
    def test_init_cx_override(self, google_search_env):
        """
        Purpose: Verify cx param overrides the GOOGLE_SEARCH_ENGINE_ID env var.
        Why this matters: Per-request engine ID override is used for multi-tenant setups.
        Setup summary: Pass cx in params and assert it takes precedence.
        """
        params = GoogleSearchParams(cx="override-cx")
        gs = GoogleSearch(params)
        assert gs.engine_id == "override-cx"

    @pytest.mark.ai
    def test_missing_api_key(self, monkeypatch):
        """
        Purpose: Verify missing API key raises the correct exception.
        Why this matters: Clear errors prevent silent failures in production.
        Setup summary: Unset the API key env var and expect GoogleSearchAPIKeyNotSetException.
        """
        monkeypatch.setenv("GOOGLE_SEARCH_API_ENDPOINT", "https://x.com")
        monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "cx")
        monkeypatch.delenv("GOOGLE_SEARCH_API_KEY", raising=False)
        with pytest.raises(GoogleSearchAPIKeyNotSetException):
            GoogleSearch(GoogleSearchParams())

    @pytest.mark.ai
    def test_missing_api_endpoint(self, monkeypatch):
        """
        Purpose: Verify missing API endpoint raises the correct exception.
        Why this matters: Clear errors prevent silent failures in production.
        Setup summary: Unset the endpoint env var and expect GoogleSearchAPIEndpointNotSetException.
        """
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "key")
        monkeypatch.delenv("GOOGLE_SEARCH_API_ENDPOINT", raising=False)
        monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "cx")
        with pytest.raises(GoogleSearchAPIEndpointNotSetException):
            GoogleSearch(GoogleSearchParams())

    @pytest.mark.ai
    def test_missing_engine_id(self, monkeypatch):
        """
        Purpose: Verify missing engine ID raises the correct exception.
        Why this matters: Clear errors prevent silent failures in production.
        Setup summary: Unset the engine ID env var and expect GoogleSearchEngineIDNotSetException.
        """
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "key")
        monkeypatch.setenv("GOOGLE_SEARCH_API_ENDPOINT", "https://x.com")
        monkeypatch.delenv("GOOGLE_SEARCH_ENGINE_ID", raising=False)
        with pytest.raises(GoogleSearchEngineIDNotSetException):
            GoogleSearch(GoogleSearchParams())


class TestGoogleSearchSearch:
    @pytest.mark.ai
    async def test_search_returns_results(self, google_search_env):
        """
        Purpose: Verify a successful search returns mapped WebSearchResult objects.
        Why this matters: This is the primary happy-path for the Google search flow.
        Setup summary: Mock AsyncClient.get to return a valid response, call search, assert results.
        """
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

        with patch(
            "unique_search_proxy.core.google_search.search.AsyncClient",
            return_value=mock_client,
        ):
            results = await gs.search("test query")

        assert len(results) == 1
        assert results[0].url == "https://r.com"

    @pytest.mark.ai
    async def test_search_pagination(self, google_search_env):
        """
        Purpose: Verify fetch_size > 10 triggers multiple paginated API calls.
        Why this matters: Google API returns max 10 results per request; pagination is needed.
        Setup summary: Set fetchSize=15, mock the client, assert two API calls are made.
        """
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

        with patch(
            "unique_search_proxy.core.google_search.search.AsyncClient",
            return_value=FakeClient(),
        ):
            await gs.search("query")

        assert call_count == 2
