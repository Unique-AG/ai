import pytest
from pydantic import ValidationError
from unique_search_proxy_core.search_engines import (
    SearchEngineType,
    parse_search_engine_config,
)
from unique_search_proxy_core.search_engines.brave.schema import (
    BraveConfig,
    BraveSearchRequest,
)
from unique_search_proxy_core.search_engines.config_types import (
    parse_search_request,
)
from unique_search_proxy_core.search_engines.custom_api.schema import (
    CustomApiConfig,
    CustomApiRequestMethod,
    CustomApiSearchRequest,
)
from unique_search_proxy_core.search_engines.google.schema import (
    GoogleConfig,
    GoogleSearchRequest,
)
from unique_search_proxy_core.search_engines.perplexity.schema import (
    PerplexityConfig,
    PerplexitySearchRequest,
)


class TestSearchEngineConfigUnion:
    @pytest.mark.ai
    def test_google_config_accepts_engine_specific_fields(self) -> None:
        config = parse_search_engine_config(
            {
                "engine": "google",
                "fetchSize": 15,
                "dateRestrict": {"expose": False, "value": "d7"},
            },
        )
        assert isinstance(config, GoogleConfig)
        assert config.engine == SearchEngineType.GOOGLE
        assert config.fetch_size == 15
        assert config.date_restrict is not None
        assert config.date_restrict.value == "d7"

    @pytest.mark.ai
    def test_search_request_parses_flat_google_payload(self) -> None:
        req = parse_search_request(
            {
                "engine": "google",
                "query": "hello",
                "fetchSize": 8,
                "timeout": 30,
            },
        )
        assert req.engine == SearchEngineType.GOOGLE
        assert isinstance(req, GoogleSearchRequest)
        assert req.fetch_size == 8
        assert req.query == "hello"

    @pytest.mark.ai
    def test_brave_config_accepts_engine_specific_fields(self) -> None:
        config = parse_search_engine_config(
            {
                "engine": "brave",
                "fetchSize": 12,
                "safesearch": "strict",
            },
        )
        assert isinstance(config, BraveConfig)
        assert config.engine == SearchEngineType.BRAVE
        assert config.fetch_size == 12
        assert config.safesearch == "strict"

    @pytest.mark.ai
    def test_search_request_parses_flat_brave_payload(self) -> None:
        req = parse_search_request(
            {
                "engine": "brave",
                "query": "hello",
                "fetchSize": 8,
                "timeout": 30,
                "safesearch": "moderate",
            },
        )
        assert req.engine == SearchEngineType.BRAVE
        assert isinstance(req, BraveSearchRequest)
        assert req.fetch_size == 8
        assert req.query == "hello"
        assert req.safesearch == "moderate"

    @pytest.mark.ai
    def test_perplexity_config_accepts_engine_specific_fields(self) -> None:
        config = parse_search_engine_config(
            {
                "engine": "perplexity",
                "fetchSize": 12,
                "searchDomainFilter": {"expose": False, "value": ["example.com"]},
            },
        )
        assert isinstance(config, PerplexityConfig)
        assert config.engine == SearchEngineType.PERPLEXITY
        assert config.fetch_size == 12
        assert config.search_domain_filter.value == ["example.com"]

    @pytest.mark.ai
    def test_search_request_parses_flat_perplexity_payload(self) -> None:
        req = parse_search_request(
            {
                "engine": "perplexity",
                "query": "hello",
                "fetchSize": 8,
                "timeout": 30,
                "searchContextSize": "low",
            },
        )
        assert req.engine == SearchEngineType.PERPLEXITY
        assert isinstance(req, PerplexitySearchRequest)
        assert req.fetch_size == 8
        assert req.query == "hello"
        assert req.search_context_size == "low"

    @pytest.mark.ai
    def test_custom_api_config_accepts_endpoint_configuration(self) -> None:
        """
        Purpose: Verify Custom API is part of the deployment config union.
        Why this matters: Proxy configuration must recognize tenant endpoints.
        Setup summary: Parse a Custom API config and inspect its typed fields.
        """
        config = parse_search_engine_config(
            {
                "engine": "custom_api",
                "apiEndpoint": "https://api.example.com/search",
                "apiRequestMethod": "POST",
            },
        )
        assert isinstance(config, CustomApiConfig)
        assert config.engine == SearchEngineType.CUSTOM_API
        assert config.api_request_method == CustomApiRequestMethod.POST

    @pytest.mark.ai
    def test_search_request_parses_flat_custom_api_payload(self) -> None:
        """
        Purpose: Verify the search request union accepts Custom API calls.
        Why this matters: The proxy route dispatches solely from this union.
        Setup summary: Parse a flat request and assert endpoint and method values.
        """
        request = parse_search_request(
            {
                "engine": "custom_api",
                "query": "hello",
                "apiEndpoint": "https://api.example.com/search",
                "apiRequestMethod": "GET",
            },
        )
        assert isinstance(request, CustomApiSearchRequest)
        assert request.engine == SearchEngineType.CUSTOM_API
        assert request.api_endpoint == "https://api.example.com/search"

    @pytest.mark.ai
    def test_unknown_engine_rejected_by_union(self) -> None:
        with pytest.raises(ValidationError):
            parse_search_engine_config({"engine": "bing"})

    @pytest.mark.ai
    def test_registered_engine_type_enum(self) -> None:
        assert SearchEngineType.GOOGLE.value == "google"
        assert SearchEngineType.BRAVE.value == "brave"
        assert SearchEngineType.PERPLEXITY.value == "perplexity"
        assert SearchEngineType.CUSTOM_API.value == "custom_api"
        assert SearchEngineType.GOOGLE in SearchEngineType
        assert SearchEngineType.BRAVE in SearchEngineType
        assert SearchEngineType.PERPLEXITY in SearchEngineType
        assert SearchEngineType.CUSTOM_API in SearchEngineType
