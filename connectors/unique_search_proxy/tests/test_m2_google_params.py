import pytest
from pydantic import BaseModel, Field, model_validator

from unique_search_proxy.web.core.param_policy.exposable_param import (
    ExposableParam,
    merge_exposable_params_with_factory_defaults,
)
from unique_search_proxy.web.core.projection import build_llm_call_model
from unique_search_proxy.web.core.schema import camelized_model_config
from unique_search_proxy.web.core.search_engines import resolve_engine_call
from unique_search_proxy.web.core.search_engines.base import SearchEngineType
from unique_search_proxy.web.core.search_engines.google.schema import (
    ExposableStrOrNone,
    GoogleConfig,
    GoogleCredentials,
    GoogleSearchRequest,
    build_google_query_params,
)
from unique_search_proxy.web.core.search_engines.google.settings import (
    GoogleSearchSettings,
    reset_google_search_settings_for_tests,
)
from unique_search_proxy.web.core.search_engines.pagination import PageRequest
from unique_search_proxy.web.core.search_engines.params import (
    config_defaults,
    llm_exposed_field_names,
    merge_config_and_invocation,
)


class TestMergeConfigAndInvocation:
    @pytest.mark.ai
    def test_merges_config_defaults_with_call_overrides(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=False, value="d7"),
            gl=ExposableStrOrNone(expose=True, value="us"),
            fetch_size=10,
        )
        request = merge_config_and_invocation(
            config,
            {"query": "hello", "gl": "de"},
            engine=SearchEngineType.GOOGLE,
        )
        assert request.query == "hello"
        assert request.date_restrict == "d7"
        assert request.gl == "de"
        assert request.fetch_size == 10
        assert request.safe == "active"

    @pytest.mark.ai
    def test_default_override_safe_applied_when_not_in_invocation(self) -> None:
        config = GoogleConfig(safe="off")
        request = merge_config_and_invocation(
            config,
            {"query": "x"},
            engine=SearchEngineType.GOOGLE,
        )
        assert request.safe == "off"

    @pytest.mark.ai
    def test_resolve_engine_call_from_factory(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=False, value="m1"),
        )
        request = resolve_engine_call(
            config,
            {"query": "news", "gl": "ch"},
        )
        assert isinstance(request, GoogleSearchRequest)
        assert request.date_restrict == "m1"
        assert request.gl == "ch"


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


class TestGoogleProviderParams:
    @pytest.mark.ai
    def test_provider_query_params_uses_camel_case(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=False, value="d7"),
            gl=ExposableStrOrNone(expose=False, value="us"),
        )
        request = merge_config_and_invocation(
            config,
            {"query": "hello"},
            engine=SearchEngineType.GOOGLE,
        )
        dumped = config.provider_query_params_from(request)
        assert dumped == {"dateRestrict": "d7", "gl": "us", "safe": "active"}

    @pytest.mark.ai
    def test_pagination_is_separate_from_engine_params(self) -> None:
        config = GoogleConfig()
        request = merge_config_and_invocation(
            config,
            {"query": "hello"},
            engine=SearchEngineType.GOOGLE,
        )
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
            request=request,
            page=page,
        )
        assert query["q"] == "hello"
        assert query["start"] == 11
        assert query["num"] == 5
        assert "cx" in query
        assert "key" in query


class TestGoogleConfigDefaults:
    @pytest.mark.ai
    def test_search_engine_id_default_from_settings(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        reset_google_search_settings_for_tests()
        monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "env-cx")
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "key")
        config = GoogleConfig()
        assert config.search_engine_id == "env-cx"

    @pytest.mark.ai
    def test_search_engine_id_default_none_when_env_unset(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        reset_google_search_settings_for_tests()
        monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "")
        config = GoogleConfig()
        assert config.search_engine_id is None


class TestGoogleConfigPolicyJsonSchema:
    @pytest.mark.ai
    def test_exposable_param_fields_use_object_schema(self) -> None:
        schema = GoogleConfig.model_json_schema()
        gl_ref = schema["properties"]["gl"]["$ref"]
        exposable = schema["$defs"][gl_ref.rsplit("/", 1)[-1]]
        assert set(exposable["properties"]) == {"expose", "value"}
        config = GoogleConfig()
        assert config.gl.expose is False
        assert config.gl.value is None


class TestGoogleConfigExposure:
    @pytest.mark.ai
    def test_query_always_in_llm_fields(self) -> None:
        config = GoogleConfig()
        exposed = llm_exposed_field_names(config)
        assert exposed == ["query"]

    @pytest.mark.ai
    def test_inactive_gl_not_in_llm_schema(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=False, value="d7"),
        )
        assert config.gl.value is None
        assert llm_exposed_field_names(config) == ["query"]

    @pytest.mark.ai
    def test_exposed_date_restrict_appears_on_llm_schema(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=True, value="d7"),
        )
        assert "date_restrict" in llm_exposed_field_names(config)

    @pytest.mark.ai
    def test_active_expose_fields_in_llm_projection(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="us"),
            date_restrict=ExposableStrOrNone(expose=False, value="d7"),
        )
        exposed = llm_exposed_field_names(config)
        assert "gl" in exposed
        assert "date_restrict" not in exposed
        projected = build_llm_call_model(GoogleConfig, config)
        assert "query" in projected.model_fields
        assert "gl" in projected.model_fields
        assert "date_restrict" not in projected.model_fields
        projected_schema = projected.model_json_schema()
        assert set(projected_schema["required"]) == {"query", "gl"}
        gl_schema = projected_schema["properties"]["gl"]
        assert gl_schema["title"] == "Geolocation (gl)"
        assert "ISO 3166-1" in gl_schema["description"]
        assert "default" not in gl_schema

    @pytest.mark.ai
    def test_expose_without_value_inherits_field_factory_default(self) -> None:
        class _ConfigWithFactoryDefault(BaseModel):
            model_config = camelized_model_config

            knob: ExposableParam[str] = Field(
                default_factory=lambda: ExposableParam[str](
                    expose=False,
                    value="ch",
                ),
            )

            @model_validator(mode="before")
            @classmethod
            def _merge_factory(cls, data: object) -> object:
                return merge_exposable_params_with_factory_defaults(cls, data)

        parsed = _ConfigWithFactoryDefault.model_validate(
            {"knob": {"expose": True}},
        )
        assert parsed.knob.expose is True
        assert parsed.knob.value == "ch"

    @pytest.mark.ai
    def test_explicit_null_value_does_not_inherit_factory_default(self) -> None:
        config = GoogleConfig.model_validate(
            {
                "engine": "google",
                "gl": {"expose": True, "value": None},
            },
        )
        assert config.gl.value is None

    @pytest.mark.ai
    def test_non_strict_llm_schema_uses_config_default_value(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="ch"),
        )
        projected = build_llm_call_model(GoogleConfig, config, strict_required=False)
        gl_schema = projected.model_json_schema()["properties"]["gl"]
        assert gl_schema["default"] == "ch"

    @pytest.mark.ai
    def test_exposable_param_accepts_expose_without_value(self) -> None:
        config = GoogleConfig.model_validate(
            {
                "engine": "google",
                "gl": {"expose": True},
            },
        )
        assert config.gl.expose is True
        assert config.gl.value is None

    @pytest.mark.ai
    def test_config_defaults_collects_all_policy_defaults(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=False, value="d7"),
            fetch_size=5,
            safe="off",
        )
        defaults = config_defaults(config)
        assert defaults["date_restrict"] == "d7"
        assert defaults["fetch_size"] == 5
        assert defaults["safe"] == "off"

    @pytest.mark.ai
    def test_legacy_string_coerces_to_exposable_param(self) -> None:
        config = GoogleConfig.model_validate({"engine": "google", "gl": "us"})
        assert config.gl is not None
        assert config.gl.expose is False
        assert config.gl.value == "us"

    @pytest.mark.ai
    def test_field_default_factory_for_non_null_value(self) -> None:
        config = GoogleConfig.model_validate(
            {
                "engine": "google",
                "gl": {"expose": False, "value": "a"},
            },
        )
        assert config.gl is not None
        assert config.gl.value == "a"
