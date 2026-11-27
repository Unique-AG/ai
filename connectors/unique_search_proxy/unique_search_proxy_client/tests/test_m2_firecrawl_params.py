from __future__ import annotations

from typing import Any

import pytest
from unique_search_proxy_core.errors import BadRequestProxyError
from unique_search_proxy_core.search_engines.firecrawl.schema import (
    FIRECRAWL_MAX_QUERY_LENGTH,
    ExposableCategory,
    ExposableCountry,
    ExposableDomainList,
    ExposableLocation,
    ExposableTimeFilter,
    FirecrawlSearchConfig,
    FirecrawlSearchRequest,
)

from unique_search_proxy_client.web.core.search_engines.firecrawl.request_body import (
    build_firecrawl_search_body,
    is_excluded_url,
)


def _body(config: FirecrawlSearchConfig | None = None, **overrides: Any) -> dict:
    request = (config or FirecrawlSearchConfig()).merge(overrides, query="hello")
    return build_firecrawl_search_body(query="hello", request=request)


class TestFirecrawlMerge:
    @pytest.mark.ai
    def test_merge__lets_call_value_win__for_exposed_time_filter(self) -> None:
        config = FirecrawlSearchConfig(
            time_filter=ExposableTimeFilter(expose=True, value="qdr:w"),
            country=ExposableCountry(expose=False, value="CH"),
            fetch_size=5,
        )

        request = config.merge({"timeFilter": "qdr:d"}, query="hello")

        assert isinstance(request, FirecrawlSearchRequest)
        assert request.query == "hello"
        assert request.time_filter == "qdr:d"
        assert request.country == "CH"
        assert request.fetch_size == 5
        assert request.sources == "web"


class TestFirecrawlRequestBody:
    @pytest.mark.ai
    def test_build_body__asks_for_previews_only__by_default(self) -> None:
        assert _body() == {
            "query": "hello",
            "limit": 10,
            "sources": ["web"],
            "timeout": 30000,
            "ignoreInvalidURLs": True,
        }

    @pytest.mark.ai
    def test_build_body__maps_search_options__to_firecrawl_fields(self) -> None:
        config = FirecrawlSearchConfig(
            highlights=False,
            safe_search=True,
            sort_by_date=True,
            time_filter=ExposableTimeFilter(expose=False, value="qdr:w"),
            category=ExposableCategory(expose=False, value="pdf"),
        )

        body = _body(config)

        assert body["highlights"] is False
        assert body["safe"] is True
        assert body["tbs"] == "sbd:1,qdr:w"
        assert body["categories"] == ["pdf"]

    @pytest.mark.ai
    def test_build_body__maps_optional_settings__to_firecrawl_fields(self) -> None:
        config = FirecrawlSearchConfig(
            time_filter=ExposableTimeFilter(expose=False, value="qdr:w"),
            country=ExposableCountry(expose=False, value="CH"),
            location=ExposableLocation(expose=False, value="Zurich,Switzerland"),
        )

        body = _body(config)

        assert body["tbs"] == "qdr:w"
        assert body["country"] == "CH"
        assert body["location"] == "Zurich,Switzerland"

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("enterprise", "expected"),
        [(None, None), ([], None), (["zdr"], ["zdr"])],
        ids=["unset", "empty", "zdr"],
    )
    def test_build_body__sends_enterprise__only_when_a_mode_is_set(
        self,
        enterprise: list[str] | None,
        expected: list[str] | None,
    ) -> None:
        request = FirecrawlSearchConfig().merge({}, query="hello")

        body = build_firecrawl_search_body(
            query="hello", request=request, enterprise=enterprise
        )

        assert body.get("enterprise") == expected

    @pytest.mark.ai
    def test_build_body__truncates_query__above_firecrawl_limit(self) -> None:
        query = "a" * (FIRECRAWL_MAX_QUERY_LENGTH + 20)
        request = FirecrawlSearchConfig().merge({}, query=query)

        body = build_firecrawl_search_body(query=query, request=request)

        assert len(body["query"]) == FIRECRAWL_MAX_QUERY_LENGTH


class TestFirecrawlDomainFilters:
    @pytest.mark.ai
    def test_build_body__sends_exclude_domains__without_an_include_list(self) -> None:
        body = _body(FirecrawlSearchConfig(exclude_domains=[" Example.com ", "b.org."]))

        assert body["excludeDomains"] == ["example.com", "b.org"]
        assert "includeDomains" not in body

    @pytest.mark.ai
    def test_build_body__removes_excluded_hosts__from_the_include_list(self) -> None:
        config = FirecrawlSearchConfig(
            include_domains=ExposableDomainList(
                expose=False,
                value=["snb.ch", "blocked.com", "news.blocked.com"],
            ),
            exclude_domains=["blocked.com"],
        )

        body = _body(config)

        assert body["includeDomains"] == ["snb.ch"]
        assert "excludeDomains" not in body

    @pytest.mark.ai
    def test_is_excluded_url__catches_excluded_subdomain__of_an_included_host(
        self,
    ) -> None:
        config = FirecrawlSearchConfig(
            include_domains=ExposableDomainList(expose=False, value=["example.com"]),
            exclude_domains=["Private.Example.com"],
        )

        body = _body(config)

        assert body["includeDomains"] == ["example.com"]
        assert is_excluded_url("https://private.example.com/a", config.exclude_domains)
        assert is_excluded_url(
            "https://x.private.example.com/a", config.exclude_domains
        )
        assert not is_excluded_url("https://www.example.com/a", config.exclude_domains)
        assert not is_excluded_url("https://example.com/a", [])

    @pytest.mark.ai
    def test_is_excluded_url__drops_unreadable_url__when_domains_are_excluded(
        self,
    ) -> None:
        assert is_excluded_url("https://[bad", ["blocked.com"])
        assert not is_excluded_url("https://[bad", [])

    @pytest.mark.ai
    def test_build_body__rejects_search__when_every_include_domain_is_excluded(
        self,
    ) -> None:
        config = FirecrawlSearchConfig(
            include_domains=ExposableDomainList(expose=False, value=["blocked.com"]),
            exclude_domains=["blocked.com"],
        )

        with pytest.raises(BadRequestProxyError, match="also excluded"):
            _body(config)


class TestFirecrawlConfigExposure:
    @pytest.mark.ai
    def test_exposed_params__contain_only_time_filter__by_default(self) -> None:
        exposed = FirecrawlSearchConfig().exposed_params_model()

        assert exposed is not None
        assert set(exposed.model_json_schema()["properties"]) == {"timeFilter"}

    @pytest.mark.ai
    def test_exposed_params__include_domains__when_admin_exposes_them(self) -> None:
        config = FirecrawlSearchConfig(
            include_domains=ExposableDomainList(expose=True, value=None),
        )

        exposed = config.exposed_params_model()

        assert exposed is not None
        properties = exposed.model_json_schema()["properties"]
        assert "includeDomains" in properties
        assert "excludeDomains" not in properties


class TestFirecrawlConfigValidation:
    @pytest.mark.ai
    def test_config__uses_defaults__when_dropdowns_are_null(self) -> None:
        config = FirecrawlSearchConfig.model_validate(
            {"engine": "firecrawl", "sources": None, "zeroDataRetention": None}
        )

        assert config.sources == "web"
        assert config.zero_data_retention == "deployment"

    @pytest.mark.ai
    def test_build_body__sends_both_sources__for_web_and_news(self) -> None:
        body = _body(FirecrawlSearchConfig(sources="web_and_news"))

        assert body["sources"] == ["web", "news"]


class TestFirecrawlConfigForm:
    @pytest.mark.ai
    def test_json_schema__labels_time_filter_codes__for_the_admin_form(self) -> None:
        defs = FirecrawlSearchConfig.model_json_schema()["$defs"]
        time_filter = next(
            branch
            for definition in defs.values()
            for branch in definition.get("properties", {})
            .get("value", {})
            .get("anyOf", [])
            if branch.get("title") == "Recent results only"
        )

        assert "enum" not in time_filter
        assert time_filter["oneOf"] == [
            {"const": "qdr:h", "title": "Past hour"},
            {"const": "qdr:d", "title": "Past day"},
            {"const": "qdr:w", "title": "Past week"},
            {"const": "qdr:m", "title": "Past month"},
            {"const": "qdr:y", "title": "Past year"},
        ]

    @pytest.mark.ai
    def test_exposed_params__keep_plain_time_filter_codes__for_the_model(
        self,
    ) -> None:
        schema = FirecrawlSearchConfig().exposed_params_model().model_json_schema()

        assert schema["properties"]["timeFilter"]["anyOf"][0]["enum"] == [
            "qdr:h",
            "qdr:d",
            "qdr:w",
            "qdr:m",
            "qdr:y",
        ]
