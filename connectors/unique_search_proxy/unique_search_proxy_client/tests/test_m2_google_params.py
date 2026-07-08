import pytest
from pydantic import BaseModel, Field, ValidationError, model_validator
from unique_search_proxy_core.errors import EngineNotConfiguredError
from unique_search_proxy_core.param_policy.exposable_param import (
    ExposableParam,
    merge_exposable_params_with_factory_defaults,
)
from unique_search_proxy_core.param_policy.resolver import ConfigRequestResolver
from unique_search_proxy_core.schema import camelized_model_config
from unique_search_proxy_core.search_engines.google.schema import (
    ExposableStrOrNone,
    GoogleConfig,
    GoogleSearchRequest,
)

from unique_search_proxy_client.web.core.search_engines import resolve_engine_call
from unique_search_proxy_client.web.core.search_engines.google.pagination import (
    iter_google_page_requests,
)
from unique_search_proxy_client.web.core.search_engines.google.query_params import (
    build_google_query_params,
)
from unique_search_proxy_client.web.core.search_engines.pagination import PageRequest
from unique_search_proxy_client.web.settings.providers.google import (
    _get_google_search_credentials,
)
from unique_search_proxy_client.web.settings.secret_str import NOT_PROVIDED


class TestMergeConfigAndInvocation:
    @pytest.mark.ai
    def test_merges_config_defaults_with_call_overrides(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=False, value="d7"),
            gl=ExposableStrOrNone(expose=True, value="us"),
            fetch_size=10,
        )
        request = resolve_engine_call(
            config,
            {"query": "hello", "gl": "de"},
        )
        assert request.query == "hello"
        assert request.date_restrict == "d7"
        assert request.gl == "de"
        assert request.fetch_size == 10
        assert request.safe == "active"

    @pytest.mark.ai
    def test_default_override_safe_applied_when_not_in_invocation(self) -> None:
        config = GoogleConfig(safe="off")
        request = resolve_engine_call(
            config,
            {"query": "x"},
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


class TestGoogleProviderParams:
    @pytest.mark.ai
    def test_provider_query_params_uses_camel_case(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=False, value="d7"),
            gl=ExposableStrOrNone(expose=False, value="us"),
        )
        request = resolve_engine_call(
            config,
            {"query": "hello"},
        )
        dumped = ConfigRequestResolver.provider_query_params(request, GoogleConfig)
        assert dumped == {"dateRestrict": "d7", "gl": "us", "safe": "active"}

    @pytest.mark.ai
    def test_google_page_offsets_use_one_based_start_index(self) -> None:
        pages = list(iter_google_page_requests(15))
        assert [(page.offset, page.count) for page in pages] == [(1, 10), (11, 5)]

    @pytest.mark.ai
    def test_pagination_is_separate_from_engine_params(self) -> None:
        config = GoogleConfig()
        request = resolve_engine_call(
            config,
            {"query": "hello"},
        )
        page = PageRequest(page_index=2, offset=11, count=5)
        query = build_google_query_params(
            query="hello",
            api_key="key",
            search_engine_id="cx",
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
    def test_search_engine_id_default_none_on_config_model(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "env-cx")
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "key")
        config = GoogleConfig()
        assert config.search_engine_id is None

    @pytest.mark.ai
    def test_check_credentials_at_call_time(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", NOT_PROVIDED)
        monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", NOT_PROVIDED)
        credentials = _get_google_search_credentials()
        with pytest.raises(EngineNotConfiguredError) as exc_info:
            credentials.check_credentials()
        assert "GOOGLE_SEARCH_API_KEY" in exc_info.value.missing_env_vars

    @pytest.mark.ai
    def test_search_engine_id_default_none_when_env_unset(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
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
        exposed = ConfigRequestResolver.exposed_field_names(config)
        assert exposed == ["query"]

    @pytest.mark.ai
    def test_inactive_gl_not_in_llm_schema(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=False, value="d7"),
        )
        assert config.gl.value is None
        assert ConfigRequestResolver.exposed_field_names(config) == ["query"]

    @pytest.mark.ai
    def test_exposed_date_restrict_appears_on_llm_schema(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=True, value="d7"),
        )
        assert "date_restrict" in ConfigRequestResolver.exposed_field_names(config)

    @pytest.mark.ai
    def test_active_expose_fields_in_llm_projection(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="us"),
            date_restrict=ExposableStrOrNone(expose=False, value="d7"),
        )
        exposed = ConfigRequestResolver.exposed_field_names(config)
        assert "gl" in exposed
        assert "date_restrict" not in exposed
        projected = ConfigRequestResolver.call_schema(config)
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
        projected = ConfigRequestResolver.call_schema(config, strict=False)
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
        defaults = ConfigRequestResolver.resolve_values(config)
        assert defaults["date_restrict"] == "d7"
        assert defaults["fetch_size"] == 5
        assert defaults["safe"] == "off"

    @pytest.mark.ai
    def test_bare_string_rejected_for_exposable_field(self) -> None:
        # Legacy bare-scalar values are no longer coerced; a stored config must
        # use the explicit {expose, value} shape (handled by the migration).
        with pytest.raises(ValidationError):
            GoogleConfig.model_validate({"engine": "google", "gl": "us"})

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
