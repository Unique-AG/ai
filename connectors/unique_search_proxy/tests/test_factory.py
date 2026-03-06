import pytest
from core import get_search_engine
from core.google_search.search import GoogleSearch
from core.schema import SearchEngineType
from core.vertexai.search import VertexAISearchEngine


class TestGetSearchEngine:
    @pytest.mark.ai
    def test_google(self):
        """
        Purpose: Verify GOOGLE engine type returns the GoogleSearch class.
        Why this matters: Incorrect factory mapping would route searches to the wrong engine.
        Setup summary: Call get_search_engine with GOOGLE and assert the returned class.
        """
        assert get_search_engine(SearchEngineType.GOOGLE) is GoogleSearch

    @pytest.mark.ai
    def test_vertexai(self):
        """
        Purpose: Verify VERTEXAI engine type returns the VertexAISearchEngine class.
        Why this matters: Incorrect factory mapping would route searches to the wrong engine.
        Setup summary: Call get_search_engine with VERTEXAI and assert the returned class.
        """
        assert get_search_engine(SearchEngineType.VERTEXAI) is VertexAISearchEngine

    @pytest.mark.ai
    def test_invalid_type(self):
        """
        Purpose: Verify an unknown engine type raises ValueError.
        Why this matters: Invalid config should fail fast rather than silently misbehave.
        Setup summary: Call with a nonexistent type and expect ValueError.
        """
        with pytest.raises(ValueError, match="Invalid search engine type"):
            get_search_engine("nonexistent")
