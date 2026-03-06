import pytest
from core.schema import SearchEngineType, WebSearchResult, WebSearchResults


class TestSearchEngineType:
    def test_google_value(self):
        assert SearchEngineType.GOOGLE == "google"

    def test_vertexai_value(self):
        assert SearchEngineType.VERTEXAI == "vertexai"

    def test_is_str_enum(self):
        assert isinstance(SearchEngineType.GOOGLE, str)


class TestWebSearchResult:
    def test_basic_creation(self):
        r = WebSearchResult(url="https://a.com", title="A", snippet="snip")
        assert r.url == "https://a.com"
        assert r.title == "A"
        assert r.snippet == "snip"
        assert r.content == ""

    def test_with_content(self):
        r = WebSearchResult(url="u", title="t", snippet="s", content="body")
        assert r.content == "body"

    def test_camel_case_serialization(self):
        r = WebSearchResult(url="u", title="t", snippet="s")
        dumped = r.model_dump(by_alias=True)
        assert "url" in dumped
        assert "title" in dumped
        assert "snippet" in dumped

    def test_camel_case_deserialization(self):
        data = {"url": "u", "title": "t", "snippet": "s", "content": "c"}
        r = WebSearchResult.model_validate(data)
        assert r.content == "c"


class TestWebSearchResults:
    def test_empty_results(self):
        results = WebSearchResults(results=[])
        assert results.results == []

    def test_multiple_results(self):
        items = [
            WebSearchResult(url="u1", title="t1", snippet="s1"),
            WebSearchResult(url="u2", title="t2", snippet="s2"),
        ]
        results = WebSearchResults(results=items)
        assert len(results.results) == 2


class TestGoogleSearchQueryParams:
    def test_creation(self):
        from core.google_search.schema import GoogleSearchQueryParams

        p = GoogleSearchQueryParams(q="test", cx="cx1", key="k1", start=1, num=10)
        assert p.q == "test"
        assert p.cx == "cx1"
        assert p.start == 1
        assert p.num == 10

    def test_missing_required_field(self):
        from core.google_search.schema import GoogleSearchQueryParams

        with pytest.raises(Exception):
            GoogleSearchQueryParams(cx="cx1", key="k1", start=1, num=10)


class TestGoogleSearchModels:
    def test_google_search_params_defaults(self):
        from core.google_search.search import GoogleSearchParams

        p = GoogleSearchParams()
        assert p.cx is None
        assert p.fetch_size == 10

    def test_google_search_params_custom(self):
        from core.google_search.search import GoogleSearchParams

        p = GoogleSearchParams.model_validate({"cx": "custom-cx", "fetchSize": 50})
        assert p.cx == "custom-cx"
        assert p.fetch_size == 50

    def test_google_search_params_fetch_size_bounds(self):
        from core.google_search.search import GoogleSearchParams

        with pytest.raises(Exception):
            GoogleSearchParams.model_validate({"fetchSize": 0})
        with pytest.raises(Exception):
            GoogleSearchParams.model_validate({"fetchSize": 101})

    def test_google_search_request_defaults(self):
        from core.google_search.search import GoogleSearchRequest

        req = GoogleSearchRequest(query="test query")
        assert req.search_engine == SearchEngineType.GOOGLE
        assert req.timeout == 10
        assert req.params.fetch_size == 10

    def test_google_search_request_camel_case(self):
        from core.google_search.search import GoogleSearchRequest

        data = {
            "searchEngine": "google",
            "query": "test",
            "timeout": 30,
            "params": {"fetchSize": 20},
        }
        req = GoogleSearchRequest.model_validate(data)
        assert req.params.fetch_size == 20
        assert req.timeout == 30


class TestVertexAiModels:
    def test_vertex_params_defaults(self):
        from core.vertexai.search import VertexAiParams

        p = VertexAiParams()
        assert p.model_name == "gemini-2.5-flash"
        assert p.entreprise_search is False
        assert p.system_instruction is None
        assert p.resolve_urls is True

    def test_vertex_params_custom(self):
        from core.vertexai.search import VertexAiParams

        p = VertexAiParams.model_validate(
            {
                "modelName": "gemini-pro",
                "entrepriseSearch": True,
                "systemInstruction": "custom",
                "resolveUrls": False,
            }
        )
        assert p.model_name == "gemini-pro"
        assert p.entreprise_search is True

    def test_vertex_request_defaults(self):
        from core.vertexai.search import VertexAiRequest

        req = VertexAiRequest(query="test")
        assert req.search_engine == SearchEngineType.VERTEXAI
        assert req.params.model_name == "gemini-2.5-flash"

    def test_vertex_request_camel_case(self):
        from core.vertexai.search import VertexAiRequest

        data = {
            "searchEngine": "vertexai",
            "query": "q",
            "params": {"modelName": "gemini-pro", "resolveUrls": False},
        }
        req = VertexAiRequest.model_validate(data)
        assert req.params.model_name == "gemini-pro"
        assert req.params.resolve_urls is False


class TestSearchRequestValidation:
    def test_empty_query_rejected(self):
        from core.google_search.search import GoogleSearchRequest

        with pytest.raises(Exception):
            GoogleSearchRequest(query="")

    def test_timeout_too_low(self):
        from core.google_search.search import GoogleSearchRequest

        with pytest.raises(Exception):
            GoogleSearchRequest(query="test", timeout=0)

    def test_timeout_too_high(self):
        from core.google_search.search import GoogleSearchRequest

        with pytest.raises(Exception):
            GoogleSearchRequest(query="test", timeout=601)
