import pytest
from unique_search_proxy_core.param_policy.resolver import ConfigRequestResolver
from unique_search_proxy_core.search_engines.config_types import parse_search_request
from unique_search_proxy_core.search_engines.perplexity.schema import (
    ExposableDomainFilter,
    ExposableRecencyFilter,
    ExposableStrOrNone,
    PerplexityConfig,
    PerplexitySearchRequest,
)

from unique_search_proxy_client.web.core.search_engines import resolve_engine_call
from unique_search_proxy_client.web.core.search_engines.perplexity.request_body import (
    build_perplexity_request_body,
)


class TestPerplexityMergeConfigAndInvocation:
    @pytest.mark.ai
    def test_merges_plain_defaults_and_exposable_values(self) -> None:
        config = PerplexityConfig(
            country=ExposableStrOrNone(expose=False, value="US"),
            search_context_size="high",
            fetch_size=5,
        )
        request = resolve_engine_call(
            config,
            {"query": "hello"},
        )
        assert isinstance(request, PerplexitySearchRequest)
        assert request.query == "hello"
        assert request.country == "US"
        assert request.search_context_size == "high"
        assert request.fetch_size == 5


class TestPerplexityProviderParams:
    @pytest.mark.ai
    def test_request_body_serializes_optional_fields(self) -> None:
        config = PerplexityConfig(
            country=ExposableStrOrNone(expose=False, value="CH"),
            search_recency_filter=ExposableRecencyFilter(expose=False, value="week"),
            max_tokens=512,
            max_tokens_per_page=128,
        )
        request = resolve_engine_call(
            config,
            {"query": "hello", "fetch_size": 3},
        )
        body = build_perplexity_request_body(query="hello", request=request)
        assert body == {
            "query": "hello",
            "max_results": 3,
            "country": "CH",
            "search_recency_filter": "week",
            "max_tokens": 512,
            "max_tokens_per_page": 128,
        }

    @pytest.mark.ai
    def test_flat_search_payload_parses(self) -> None:
        request = parse_search_request(
            {
                "engine": "perplexity",
                "query": "unique ag",
                "fetchSize": 5,
                "searchDomainFilter": ["example.com"],
                "searchRecencyFilter": "day",
            },
        )
        body = build_perplexity_request_body(
            query=request.query,  # type: ignore[attr-defined]
            request=request,
        )
        assert body["query"] == "unique ag"
        assert body["max_results"] == 5
        assert body["search_domain_filter"] == ["example.com"]
        assert body["search_recency_filter"] == "day"


class TestPerplexityConfigExposure:
    @pytest.mark.ai
    def test_query_only_when_nothing_exposed(self) -> None:
        config = PerplexityConfig()
        assert ConfigRequestResolver.exposed_field_names(config) == ["query"]

    @pytest.mark.ai
    def test_exposed_country_appears_on_llm_schema(self) -> None:
        config = PerplexityConfig(
            country=ExposableStrOrNone(expose=True, value="US"),
            search_domain_filter=ExposableDomainFilter(
                expose=False, value=["example.com"]
            ),
        )
        exposed = ConfigRequestResolver.exposed_field_names(config)
        assert "country" in exposed
        assert "search_domain_filter" not in exposed
        projected = ConfigRequestResolver.call_schema(config)
        assert "country" in projected.model_fields
        assert "search_domain_filter" not in projected.model_fields

    @pytest.mark.ai
    def test_search_context_size_not_exposable(self) -> None:
        config = PerplexityConfig(
            country=ExposableStrOrNone(expose=True, value="US"),
        )
        exposed = ConfigRequestResolver.exposed_field_names(config)
        assert "search_context_size" not in exposed
        projected = ConfigRequestResolver.call_schema(config)
        assert "search_context_size" not in projected.model_fields

    @pytest.mark.ai
    def test_config_defaults_collects_plain_and_exposable_values(self) -> None:
        config = PerplexityConfig(
            country=ExposableStrOrNone(expose=False, value="CH"),
            search_context_size="medium",
            max_tokens=256,
            max_tokens_per_page=64,
            fetch_size=8,
        )
        defaults = ConfigRequestResolver.resolve_values(config)
        assert defaults["country"] == "CH"
        assert defaults["search_context_size"] == "medium"
        assert defaults["max_tokens"] == 256
        assert defaults["max_tokens_per_page"] == 64
        assert defaults["fetch_size"] == 8
