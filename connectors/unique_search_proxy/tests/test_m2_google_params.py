import pytest
from pydantic import ValidationError

from unique_search_proxy.web.core.projection import project_call_schema
from unique_search_proxy.web.core.search_engines import resolve_engine_call
from unique_search_proxy.web.core.search_engines.google.schema import (
    GoogleConfig,
    GoogleCredentials,
    GoogleEngineParameters,
    GoogleSearchCall,
    build_google_query_params,
)
from unique_search_proxy.web.core.search_engines.google.settings import (
    GoogleSearchSettings,
)
from unique_search_proxy.web.core.search_engines.pagination import PageRequest
from unique_search_proxy.web.core.search_engines.params import (
    ParamExposure,
    resolve_search_call,
    validate_exposed_fields,
)


class TestResolveSearchCall:
    @pytest.mark.ai
    def test_merges_config_defaults_with_call_overrides(self) -> None:
        config = GoogleConfig(date_restrict="d7", gl="us")
        call = resolve_search_call(
            GoogleSearchCall,
            GoogleEngineParameters,
            config,
            {"query": "hello", "gl": "de"},
        )
        assert call.query == "hello"
        assert call.date_restrict == "d7"
        assert call.gl == "de"

    @pytest.mark.ai
    def test_resolve_engine_call_from_factory(self) -> None:
        config = GoogleConfig(date_restrict="m1")
        call = resolve_engine_call(
            config,
            {"query": "news", "gl": "ch"},
        )
        assert isinstance(call, GoogleSearchCall)
        assert call.date_restrict == "m1"
        assert call.gl == "ch"


class TestGoogleCredentials:
    @pytest.mark.ai
    def test_from_settings_uses_config_override_for_cx(self) -> None:
        settings = GoogleSearchSettings(
            google_search_api_key="key",
            google_search_engine_id="env-cx",
            google_search_api_endpoint="https://example.com/search",
        )
        credentials = GoogleCredentials.from_settings(
            settings,
            search_engine_id="config-cx",
        )
        assert credentials.search_engine_id == "config-cx"

    @pytest.mark.ai
    def test_from_settings_falls_back_to_env_cx(self) -> None:
        settings = GoogleSearchSettings(
            google_search_api_key="key",
            google_search_engine_id="env-cx",
            google_search_api_endpoint="https://example.com/search",
        )
        credentials = GoogleCredentials.from_settings(settings)
        assert credentials.search_engine_id == "env-cx"


class TestGoogleEngineParameters:
    @pytest.mark.ai
    def test_provider_query_params_uses_camel_case(self) -> None:
        params = GoogleEngineParameters(date_restrict="d7", gl="us")
        dumped = params.provider_query_params()
        assert dumped == {"dateRestrict": "d7", "gl": "us", "safe": "active"}

    @pytest.mark.ai
    def test_pagination_is_separate_from_engine_params(self) -> None:
        params = GoogleEngineParameters()
        page = PageRequest(page_index=2, offset=11, count=5)
        query = build_google_query_params(
            query="hello",
            credentials=type(
                "Creds",
                (),
                {
                    "api_key": "key",
                    "search_engine_id": "cx",
                },
            )(),
            engine=params,
            page=page,
        )
        assert query["q"] == "hello"
        assert query["start"] == 11
        assert query["num"] == 5
        assert "cx" in query
        assert "key" in query


class TestGoogleConfigExposure:
    @pytest.mark.ai
    def test_query_always_in_llm_fields(self) -> None:
        config = GoogleConfig()
        assert config.llm_field_names() == ["query"]

    @pytest.mark.ai
    def test_optional_exposure_allowlist(self) -> None:
        config = GoogleConfig(exposed_fields=["dateRestrict", "gl"])
        assert config.llm_field_names() == ["query", "date_restrict", "gl"]

    @pytest.mark.ai
    def test_fetch_size_cannot_be_exposed(self) -> None:
        with pytest.raises(ValidationError):
            GoogleConfig.model_validate(
                {"engine": "google", "exposedFields": ["fetchSize"]},
            )

    @pytest.mark.ai
    def test_query_cannot_be_listed_in_exposed_fields(self) -> None:
        with pytest.raises(ValidationError):
            GoogleConfig.model_validate(
                {"engine": "google", "exposedFields": ["query"]},
            )

    @pytest.mark.ai
    def test_search_engine_id_cannot_be_exposed(self) -> None:
        with pytest.raises(ValidationError):
            GoogleConfig.model_validate(
                {"engine": "google", "exposedFields": ["searchEngineId"]},
            )

    @pytest.mark.ai
    def test_llm_projection_includes_query_only_by_default(self) -> None:
        config = GoogleConfig()
        projected = project_call_schema(GoogleSearchCall, config.llm_field_names())
        assert "query" in projected.model_fields
        assert "date_restrict" not in projected.model_fields

    @pytest.mark.ai
    def test_exposable_metadata_on_engine_parameters(self) -> None:
        field = GoogleEngineParameters.model_fields["date_restrict"]
        assert field.json_schema_extra is not None
        assert field.json_schema_extra["exposure"] == ParamExposure.EXPOSABLE.value

    @pytest.mark.ai
    def test_validate_exposed_fields_rejects_unknown(self) -> None:
        with pytest.raises(ValueError, match="not defined"):
            validate_exposed_fields(GoogleEngineParameters, ["missing"])
