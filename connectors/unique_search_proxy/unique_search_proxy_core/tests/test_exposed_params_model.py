import pytest

from unique_search_proxy_core.search_engines.brave.schema import (
    BraveConfig,
    ExposableCountry,
    ExposableSearchLang,
)
from unique_search_proxy_core.search_engines.call_schema import (
    build_exposed_params_model,
    build_exposed_tool_field_defs,
    exposed_field_names,
    exposed_tool_fields_json_schema,
)
from unique_search_proxy_core.search_engines.google.schema import (
    ExposableStrOrNone,
    GoogleConfig,
)


class TestBuildExposedParamsModel:
    @pytest.mark.ai
    def test_returns_none_when_nothing_exposed(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=False, value="d7"),
        )
        assert build_exposed_params_model(config) is None

    @pytest.mark.ai
    def test_excludes_query_from_model(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="us"),
        )
        model = build_exposed_params_model(config)
        assert model is not None
        assert "query" not in model.model_fields
        assert "gl" in model.model_fields

    @pytest.mark.ai
    def test_exposed_fields_are_optional(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="ch"),
            date_restrict=ExposableStrOrNone(expose=True, value="d7"),
        )
        model = build_exposed_params_model(config)
        assert model is not None
        schema = model.model_json_schema()
        required = set(schema.get("required", []))
        assert "gl" not in required
        assert "dateRestrict" not in required

    @pytest.mark.ai
    def test_inherits_admin_defaults_on_exposed_fields(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="ch"),
        )
        model = build_exposed_params_model(config)
        assert model is not None
        gl_schema = model.model_json_schema()["properties"]["gl"]
        assert gl_schema.get("default") == "ch"

    @pytest.mark.ai
    def test_not_exposed_fields_absent(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="us"),
            date_restrict=ExposableStrOrNone(expose=False, value="d7"),
        )
        model = build_exposed_params_model(config)
        assert model is not None
        fields = model.model_fields
        assert "gl" in fields
        assert "date_restrict" not in fields


class TestBuildExposedToolFieldDefs:
    @pytest.mark.ai
    def test_exposed_field_names_excludes_query(self) -> None:
        config = GoogleConfig(gl=ExposableStrOrNone(expose=True, value="us"))
        assert exposed_field_names(config) == ["gl"]

    @pytest.mark.ai
    def test_returns_none_when_nothing_exposed(self) -> None:
        config = GoogleConfig()
        assert build_exposed_tool_field_defs(config) is None

    @pytest.mark.ai
    def test_flat_fields_description_only_schema(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="ch"),
            date_restrict=ExposableStrOrNone(expose=True, value="d7"),
        )
        schema = exposed_tool_fields_json_schema(config)
        required = set(schema.get("required", []))
        assert "gl" not in required
        assert "date_restrict" not in required
        gl_prop = schema["properties"]["gl"]
        assert "description" in gl_prop
        assert "title" not in gl_prop
        assert "default" not in gl_prop
        assert gl_prop["anyOf"] == [{"type": "string"}, {"type": "null"}]

    @pytest.mark.ai
    def test_no_admin_defaults_in_tool_schema(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="ch"),
        )
        gl_prop = exposed_tool_fields_json_schema(config)["properties"]["gl"]
        assert gl_prop.get("default") is None
        assert "default" not in gl_prop

    @pytest.mark.ai
    def test_brave_literal_enum_exposed_fields_emit_enum_schema(self) -> None:
        config = BraveConfig(
            country=ExposableCountry(expose=True, value="US"),
            search_lang=ExposableSearchLang(expose=True, value="en"),
        )
        schema = exposed_tool_fields_json_schema(config)
        country_prop = schema["properties"]["country"]
        country_string = country_prop["anyOf"][0]
        assert country_string["type"] == "string"
        assert "enum" in country_string
        assert "US" in country_string["enum"]
        search_lang_prop = schema["properties"]["search_lang"]
        search_lang_string = search_lang_prop["anyOf"][0]
        assert "enum" in search_lang_string
        assert "en" in search_lang_string["enum"]
