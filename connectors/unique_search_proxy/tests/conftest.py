import pytest


@pytest.fixture
def google_search_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "test-api-key")
    monkeypatch.setenv("GOOGLE_SEARCH_API_ENDPOINT", "https://example.com/search")
    monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "test-engine-id")
