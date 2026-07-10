import pytest
from pydantic import ValidationError
from unique_search_proxy_core.search_engines.brave.schema import (
    BraveConfig,
    BraveSearchRequest,
    ExposableCountry,
    ExposableSearchLang,
    ExposableStrOrNone,
)
from unique_search_proxy_core.search_engines.config_types import parse_search_request

from unique_search_proxy_client.web.core.search_engines.brave.pagination import (
    iter_brave_page_requests,
)
from unique_search_proxy_client.web.core.search_engines.brave.query_params import (
    build_brave_query_params,
)
from unique_search_proxy_client.web.core.search_engines.pagination import PageRequest


class TestBraveMerge:
    @pytest.mark.ai
    def test_merges_plain_defaults_and_exposable_values(self) -> None:
        config = BraveConfig(
            country=ExposableCountry(expose=False, value="CH"),
            freshness=ExposableStrOrNone(expose=True, value="pw"),
            fetch_size=5,
        )
        request = config.merge({"freshness": "pd"}, query="hello")
        assert isinstance(request, BraveSearchRequest)
        assert request.query == "hello"
        assert request.country == "CH"
        assert request.freshness == "pd"
        assert request.fetch_size == 5
        assert request.extra_snippets is True
        assert request.safesearch == "moderate"

    @pytest.mark.ai
    def test_safesearch_default_moderate(self) -> None:
        request = BraveConfig().merge({}, query="x")
        assert request.safesearch == "moderate"


class TestBraveProviderParams:
    @pytest.mark.ai
    def test_provider_query_params_uses_snake_case(self) -> None:
        config = BraveConfig(
            country=ExposableCountry(expose=False, value="DE"),
            search_lang=ExposableSearchLang(expose=False, value="de"),
        )
        request = config.merge({}, query="hello")
        dumped = BraveConfig.provider_query_params(request, by_alias=False)
        assert dumped == {
            "country": "DE",
            "extra_snippets": True,
            "include_fetch_metadata": False,
            "operators": True,
            "safesearch": "moderate",
            "search_lang": "de",
            "spellcheck": False,
            "summary": True,
            "text_decorations": True,
            "ui_lang": "en-US",
        }

    @pytest.mark.ai
    def test_curl_style_body_serializes_summary_and_extra_snippets(self) -> None:
        request = parse_search_request(
            {
                "engine": "brave",
                "query": "unique ag",
                "fetchSize": 5,
                "timeout": 30,
                "summary": True,
                "extraSnippets": False,
            },
        )
        params = build_brave_query_params(
            query=request.query,  # type: ignore[attr-defined]
            request=request,
            page=PageRequest(page_index=0, offset=0, count=5),
        )
        assert params["summary"] is True
        assert params["extra_snippets"] is False
        assert params["q"] == "unique ag"
        assert params["count"] == 5

    @pytest.mark.ai
    def test_brave_page_offsets_are_page_indexes_not_result_offsets(self) -> None:
        pages = list(iter_brave_page_requests(25))
        assert [(page.offset, page.count) for page in pages] == [(0, 20), (1, 5)]

    @pytest.mark.ai
    def test_pagination_is_separate_from_engine_params(self) -> None:
        request = BraveConfig().merge({}, query="hello")
        page = PageRequest(page_index=2, offset=1, count=5)
        query = build_brave_query_params(
            query="hello",
            request=request,
            page=page,
        )
        assert query["q"] == "hello"
        assert query["offset"] == 1
        assert query["count"] == 5
        assert "safesearch" in query

    @pytest.mark.ai
    def test_count_and_offset_not_on_request_model(self) -> None:
        request_fields = BraveSearchRequest.model_fields
        assert "count" not in request_fields
        assert "offset" not in request_fields


class TestBraveConfigPolicyJsonSchema:
    @pytest.mark.ai
    def test_exposable_param_fields_use_object_schema(self) -> None:
        schema = BraveConfig.model_json_schema()
        country_ref = schema["properties"]["country"]["$ref"]
        exposable = schema["$defs"][country_ref.rsplit("/", 1)[-1]]
        assert set(exposable["properties"]) == {"expose", "value"}
        config = BraveConfig()
        assert config.country.expose is False
        assert config.country.value == "US"
        assert config.search_lang.value == "en"
        assert config.safesearch == "moderate"


class TestBraveConfigExposure:
    @pytest.mark.ai
    def test_nothing_exposed_returns_none(self) -> None:
        assert BraveConfig().exposed_params_model() is None

    @pytest.mark.ai
    def test_exposed_freshness_appears_on_exposed_model(self) -> None:
        config = BraveConfig(
            freshness=ExposableStrOrNone(expose=True, value="pm"),
            country=ExposableCountry(expose=False, value="US"),
        )
        exposed = config.exposed_params_model()
        assert exposed is not None
        assert "freshness" in exposed.model_fields
        assert "country" not in exposed.model_fields

    @pytest.mark.ai
    def test_exposed_country_enum_surfaces_in_schema(self) -> None:
        config = BraveConfig(
            country=ExposableCountry(expose=True, value="US"),
        )
        exposed = config.exposed_params_model()
        assert exposed is not None
        country_schema = exposed.model_json_schema()["properties"]["country"]
        enum_values = country_schema["anyOf"][0]["enum"]
        assert "CH" in enum_values
        assert "default" not in country_schema
        assert "title" not in country_schema

    @pytest.mark.ai
    def test_bare_string_no_longer_coerces_to_exposable_param(self) -> None:
        with pytest.raises(ValidationError):
            BraveConfig.model_validate({"engine": "brave", "country": "DE"})

    @pytest.mark.ai
    def test_invalid_country_code_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BraveConfig.model_validate(
                {"engine": "brave", "country": {"expose": False, "value": "XX"}},
            )
