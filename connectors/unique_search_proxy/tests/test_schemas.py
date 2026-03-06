import pytest
from core.schema import SearchEngineType, WebSearchResult, WebSearchResults


class TestSearchEngineType:
    @pytest.mark.ai
    def test_google_value(self):
        """
        Purpose: Verify the GOOGLE enum member has the expected string value.
        Why this matters: Incorrect enum values break API request routing.
        Setup summary: Access the enum and assert its value.
        """
        assert SearchEngineType.GOOGLE == "google"

    @pytest.mark.ai
    def test_vertexai_value(self):
        """
        Purpose: Verify the VERTEXAI enum member has the expected string value.
        Why this matters: Incorrect enum values break API request routing.
        Setup summary: Access the enum and assert its value.
        """
        assert SearchEngineType.VERTEXAI == "vertexai"

    @pytest.mark.ai
    def test_is_str_enum(self):
        """
        Purpose: Confirm SearchEngineType members are also str instances.
        Why this matters: JSON serialization relies on str-compatibility of enum values.
        Setup summary: Check isinstance against str.
        """
        assert isinstance(SearchEngineType.GOOGLE, str)


class TestWebSearchResult:
    @pytest.mark.ai
    def test_basic_creation(self):
        """
        Purpose: Verify WebSearchResult initialises with required fields and default content.
        Why this matters: Downstream consumers depend on the default empty-string content.
        Setup summary: Create a result with mandatory fields and assert defaults.
        """
        r = WebSearchResult(url="https://a.com", title="A", snippet="snip")
        assert r.url == "https://a.com"
        assert r.title == "A"
        assert r.snippet == "snip"
        assert r.content == ""

    @pytest.mark.ai
    def test_with_content(self):
        """
        Purpose: Verify that an explicit content value overrides the default.
        Why this matters: Full-text content is used for grounded search results.
        Setup summary: Create a result with content and assert it.
        """
        r = WebSearchResult(url="u", title="t", snippet="s", content="body")
        assert r.content == "body"

    @pytest.mark.ai
    def test_camel_case_serialization(self):
        """
        Purpose: Confirm model_dump with by_alias produces camelCase keys.
        Why this matters: The API contract requires camelCase JSON responses.
        Setup summary: Dump the model with aliases and check key names.
        """
        r = WebSearchResult(url="u", title="t", snippet="s")
        dumped = r.model_dump(by_alias=True)
        assert "url" in dumped
        assert "title" in dumped
        assert "snippet" in dumped

    @pytest.mark.ai
    def test_camel_case_deserialization(self):
        """
        Purpose: Confirm model_validate correctly parses camelCase input.
        Why this matters: Incoming requests use camelCase field names.
        Setup summary: Validate a dict with camelCase keys and check parsed fields.
        """
        data = {"url": "u", "title": "t", "snippet": "s", "content": "c"}
        r = WebSearchResult.model_validate(data)
        assert r.content == "c"


class TestWebSearchResults:
    @pytest.mark.ai
    def test_empty_results(self):
        """
        Purpose: Verify the results wrapper accepts an empty list.
        Why this matters: Search may legitimately return zero results.
        Setup summary: Construct with an empty list and assert.
        """
        results = WebSearchResults(results=[])
        assert results.results == []

    @pytest.mark.ai
    def test_multiple_results(self):
        """
        Purpose: Verify the results wrapper holds multiple items.
        Why this matters: Normal search flow returns multiple results.
        Setup summary: Construct with two items and assert the count.
        """
        items = [
            WebSearchResult(url="u1", title="t1", snippet="s1"),
            WebSearchResult(url="u2", title="t2", snippet="s2"),
        ]
        results = WebSearchResults(results=items)
        assert len(results.results) == 2


class TestGoogleSearchQueryParams:
    @pytest.mark.ai
    def test_creation(self):
        """
        Purpose: Verify GoogleSearchQueryParams accepts all required fields.
        Why this matters: These params are passed directly to the Google API.
        Setup summary: Construct with all fields and assert values.
        """
        from core.google_search.schema import GoogleSearchQueryParams

        p = GoogleSearchQueryParams(q="test", cx="cx1", key="k1", start=1, num=10)
        assert p.q == "test"
        assert p.cx == "cx1"
        assert p.start == 1
        assert p.num == 10

    @pytest.mark.ai
    def test_missing_required_field(self):
        """
        Purpose: Confirm validation rejects construction without required field q.
        Why this matters: Missing query would produce invalid API requests.
        Setup summary: Omit the q field and expect a validation error.
        """
        from core.google_search.schema import GoogleSearchQueryParams

        with pytest.raises(Exception):
            GoogleSearchQueryParams(cx="cx1", key="k1", start=1, num=10)


class TestGoogleSearchModels:
    @pytest.mark.ai
    def test_google_search_params_defaults(self):
        """
        Purpose: Verify GoogleSearchParams has sensible defaults.
        Why this matters: Callers rely on defaults when no params are provided.
        Setup summary: Construct with no args and assert defaults.
        """
        from core.google_search.search import GoogleSearchParams

        p = GoogleSearchParams()
        assert p.cx is None
        assert p.fetch_size == 10

    @pytest.mark.ai
    def test_google_search_params_custom(self):
        """
        Purpose: Verify custom values are accepted via camelCase validation.
        Why this matters: API requests arrive with camelCase keys.
        Setup summary: Use model_validate with camelCase input.
        """
        from core.google_search.search import GoogleSearchParams

        p = GoogleSearchParams.model_validate({"cx": "custom-cx", "fetchSize": 50})
        assert p.cx == "custom-cx"
        assert p.fetch_size == 50

    @pytest.mark.ai
    def test_google_search_params_fetch_size_bounds(self):
        """
        Purpose: Confirm fetch_size rejects out-of-bounds values.
        Why this matters: Google API only supports 1-100 results per request.
        Setup summary: Validate with 0 and 101 and expect errors.
        """
        from core.google_search.search import GoogleSearchParams

        with pytest.raises(Exception):
            GoogleSearchParams.model_validate({"fetchSize": 0})
        with pytest.raises(Exception):
            GoogleSearchParams.model_validate({"fetchSize": 101})

    @pytest.mark.ai
    def test_google_search_request_defaults(self):
        """
        Purpose: Verify GoogleSearchRequest has correct default engine, timeout, and params.
        Why this matters: Default values determine the out-of-the-box search behaviour.
        Setup summary: Construct with query only and assert defaults.
        """
        from core.google_search.search import GoogleSearchRequest

        req = GoogleSearchRequest(query="test query")
        assert req.search_engine == SearchEngineType.GOOGLE
        assert req.timeout == 10
        assert req.params.fetch_size == 10

    @pytest.mark.ai
    def test_google_search_request_camel_case(self):
        """
        Purpose: Confirm GoogleSearchRequest deserialises camelCase input correctly.
        Why this matters: Incoming JSON uses camelCase field names.
        Setup summary: Validate from a camelCase dict and assert parsed values.
        """
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
    @pytest.mark.ai
    def test_vertex_params_defaults(self):
        """
        Purpose: Verify VertexAiParams has expected default values.
        Why this matters: Defaults determine which model and features are used.
        Setup summary: Construct with no args and assert defaults.
        """
        from core.vertexai.search import VertexAiParams

        p = VertexAiParams()
        assert p.model_name == "gemini-2.5-flash"
        assert p.entreprise_search is False
        assert p.system_instruction is None
        assert p.resolve_urls is True

    @pytest.mark.ai
    def test_vertex_params_custom(self):
        """
        Purpose: Verify custom values are parsed via camelCase model_validate.
        Why this matters: API requests provide camelCase configuration.
        Setup summary: Validate from a camelCase dict and assert custom values.
        """
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

    @pytest.mark.ai
    def test_vertex_request_defaults(self):
        """
        Purpose: Verify VertexAiRequest has correct default engine and params.
        Why this matters: Default config controls production search behaviour.
        Setup summary: Construct with query only and assert defaults.
        """
        from core.vertexai.search import VertexAiRequest

        req = VertexAiRequest(query="test")
        assert req.search_engine == SearchEngineType.VERTEXAI
        assert req.params.model_name == "gemini-2.5-flash"

    @pytest.mark.ai
    def test_vertex_request_camel_case(self):
        """
        Purpose: Confirm VertexAiRequest deserialises camelCase input correctly.
        Why this matters: Incoming JSON uses camelCase field names.
        Setup summary: Validate from a camelCase dict and assert parsed values.
        """
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
    @pytest.mark.ai
    def test_empty_query_rejected(self):
        """
        Purpose: Confirm empty query string is rejected by validation.
        Why this matters: An empty query would produce a useless API call.
        Setup summary: Construct with empty query and expect a validation error.
        """
        from core.google_search.search import GoogleSearchRequest

        with pytest.raises(Exception):
            GoogleSearchRequest(query="")

    @pytest.mark.ai
    def test_timeout_too_low(self):
        """
        Purpose: Confirm timeout=0 is rejected.
        Why this matters: Zero timeout would cause immediate request failure.
        Setup summary: Construct with timeout=0 and expect an error.
        """
        from core.google_search.search import GoogleSearchRequest

        with pytest.raises(Exception):
            GoogleSearchRequest(query="test", timeout=0)

    @pytest.mark.ai
    def test_timeout_too_high(self):
        """
        Purpose: Confirm timeout above the maximum is rejected.
        Why this matters: Excessively long timeouts could block the server.
        Setup summary: Construct with timeout=601 and expect an error.
        """
        from core.google_search.search import GoogleSearchRequest

        with pytest.raises(Exception):
            GoogleSearchRequest(query="test", timeout=601)
