import pytest
from core import get_search_engine
from core.google_search.search import GoogleSearch
from core.schema import SearchEngineType
from core.vertexai.search import VertexAISearchEngine


class TestGetSearchEngine:
    def test_google(self):
        assert get_search_engine(SearchEngineType.GOOGLE) is GoogleSearch

    def test_vertexai(self):
        assert get_search_engine(SearchEngineType.VERTEXAI) is VertexAISearchEngine

    def test_invalid_type(self):
        with pytest.raises(ValueError, match="Invalid search engine type"):
            get_search_engine("nonexistent")
