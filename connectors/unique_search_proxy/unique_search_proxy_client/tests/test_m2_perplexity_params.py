import pytest
from unique_search_proxy_core.search_engines.config_types import parse_search_request
from unique_search_proxy_core.search_engines.perplexity.schema import (
    ExposableDomainFilter,
    ExposableRecencyFilter,
    ExposableStrOrNone,
    PerplexityConfig,
    PerplexitySearchRequest,
)

from unique_search_proxy_client.web.core.search_engines.perplexity.request_body import (
    build_perplexity_request_body,
)


class TestPerplexityMerge:
    @pytest.mark.ai
    def test_merges_plain_defaults_and_exposable_values(self) -> None:
        config = PerplexityConfig(
            country=ExposableStrOrNone(expose=False, value="US"),
            search_context_size="high",
            fetch_size=5,
        )
        request = config.merge({"search_context_size": "low"}, query="hello")
        assert isinstance(request, PerplexitySearchRequest)
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
        request = config.merge({"fetch_size": 3}, query="hello")
        body = build_perplexity_request_body(query="hello", request=request)
        # Perplexity API rule: search_context_size is dropped when an explicit
        # token limit is set.
        assert body == {
            "query": "hello",
            "max_results": 3,
            "country": "CH",
            "search_recency_filter": "week",
            "max_tokens": 512,
            "max_tokens_per_page": 128,
        }

    @pytest.mark.ai
    def test_context_size_kept_without_token_limits(self) -> None:
        request = PerplexityConfig().merge({}, query="hello")
        body = build_perplexity_request_body(query="hello", request=request)
        assert body["search_context_size"] == "medium"

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
    def test_nothing_exposed_returns_none(self) -> None:
        assert PerplexityConfig().exposed_params_model() is None

    @pytest.mark.ai
    def test_exposed_country_appears_on_exposed_model(self) -> None:
        config = PerplexityConfig(
            country=ExposableStrOrNone(expose=True, value="US"),
            search_domain_filter=ExposableDomainFilter(
                expose=False, value=["example.com"]
            ),
        )
        exposed = config.exposed_params_model()
        assert exposed is not None
        assert "country" in exposed.model_fields
        assert "search_domain_filter" not in exposed.model_fields

    @pytest.mark.ai
    def test_exposed_domain_filter_uses_camel_case_alias(self) -> None:
        config = PerplexityConfig(
            search_domain_filter=ExposableDomainFilter(expose=True, value=None),
        )
        exposed = config.exposed_params_model()
        assert exposed is not None
        properties = exposed.model_json_schema()["properties"]
        assert "searchDomainFilter" in properties
        assert "search_domain_filter" not in properties
