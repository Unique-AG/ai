import pytest
from unique_search_proxy_core.projection import build_llm_call_model
from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_search_proxy_core.search_engines.config_types import parse_search_request
from unique_search_proxy_core.search_engines.params import (
    config_defaults,
    llm_exposed_field_names,
    merge_config_and_invocation,
)
from unique_search_proxy_core.search_engines.perplexity.schema import (
    ExposableDomainFilter,
    ExposableRecencyFilter,
    ExposableSearchContextSize,
    ExposableStrOrNone,
    PerplexityConfig,
    PerplexityRequest,
)

from unique_search_proxy_client.web.core.search_engines.perplexity.request_body import (
    build_perplexity_request_body,
)


class TestPerplexityMergeConfigAndInvocation:
    @pytest.mark.ai
    def test_merges_plain_defaults_and_exposable_values(self) -> None:
        config = PerplexityConfig(
            country=ExposableStrOrNone(expose=False, value="US"),
            search_context_size=ExposableSearchContextSize(expose=True, value="high"),
            fetch_size=5,
        )
        request = merge_config_and_invocation(
            config,
            {"query": "hello", "search_context_size": "low"},
            engine=SearchEngineType.PERPLEXITY,
        )
        assert isinstance(request, PerplexityRequest)
        assert request.query == "hello"
        assert request.country == "US"
        assert request.search_context_size == "low"
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
        request = merge_config_and_invocation(
            config,
            {"query": "hello", "fetch_size": 3},
            engine=SearchEngineType.PERPLEXITY,
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
        assert llm_exposed_field_names(config) == ["query"]

    @pytest.mark.ai
    def test_exposed_country_appears_on_llm_schema(self) -> None:
        config = PerplexityConfig(
            country=ExposableStrOrNone(expose=True, value="US"),
            search_domain_filter=ExposableDomainFilter(expose=False, value=["example.com"]),
        )
        exposed = llm_exposed_field_names(config)
        assert "country" in exposed
        assert "search_domain_filter" not in exposed
        projected = build_llm_call_model(PerplexityConfig, config)
        assert "country" in projected.model_fields
        assert "search_domain_filter" not in projected.model_fields

    @pytest.mark.ai
    def test_config_defaults_collects_plain_and_exposable_values(self) -> None:
        config = PerplexityConfig(
            country=ExposableStrOrNone(expose=False, value="CH"),
            search_context_size=ExposableSearchContextSize(expose=False, value="medium"),
            max_tokens=256,
            max_tokens_per_page=64,
            fetch_size=8,
        )
        defaults = config_defaults(config)
        assert defaults["country"] == "CH"
        assert defaults["search_context_size"] == "medium"
        assert defaults["max_tokens"] == 256
        assert defaults["max_tokens_per_page"] == 64
        assert defaults["fetch_size"] == 8
