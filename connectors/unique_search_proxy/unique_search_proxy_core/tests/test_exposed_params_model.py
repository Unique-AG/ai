import pytest
from pydantic import BaseModel, create_model

from unique_search_proxy_core.search_engines.brave.schema import (
    BraveConfig,
    ExposableCountry,
    ExposableSearchLang,
)
from unique_search_proxy_core.search_engines.call_schema import (
    ExposedToolParameterModel,
    build_exposed_tool_field_defs,
    exposed_field_names,
)
from unique_search_proxy_core.search_engines.google.schema import (
    ExposableStrOrNone,
    GoogleConfig,
)


def _tool_fields_schema(config: BaseModel) -> dict:
    field_defs = build_exposed_tool_field_defs(config)
    assert field_defs is not None
    model = create_model(
        "ExposedToolFields",
        __base__=ExposedToolParameterModel,
        **field_defs,
    )
    return model.model_json_schema()


class TestExposedFieldNames:
    @pytest.mark.ai
    def test_excludes_query(self) -> None:
        config = GoogleConfig(gl=ExposableStrOrNone(expose=True, value="us"))
        assert exposed_field_names(config) == ["gl"]

    @pytest.mark.ai
    def test_returns_none_when_nothing_exposed(self) -> None:
        assert build_exposed_tool_field_defs(GoogleConfig()) is None


class TestBuildExposedToolFieldDefs:
    @pytest.mark.ai
    def test_flat_fields_description_only_schema(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="ch"),
            date_restrict=ExposableStrOrNone(expose=True, value="d7"),
        )
        schema = _tool_fields_schema(config)
        required = set(schema.get("required", []))
        assert "gl" not in required
        assert "dateRestrict" not in required
        gl_prop = schema["properties"]["gl"]
        assert "description" in gl_prop
        assert "title" not in gl_prop
        assert "default" not in gl_prop
        assert gl_prop["anyOf"] == [{"type": "string"}, {"type": "null"}]

    @pytest.mark.ai
    def test_no_admin_defaults_in_tool_schema(self) -> None:
        config = GoogleConfig(gl=ExposableStrOrNone(expose=True, value="ch"))
        gl_prop = _tool_fields_schema(config)["properties"]["gl"]
        assert "default" not in gl_prop

    @pytest.mark.ai
    def test_exposed_field_uses_camel_case_alias(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=True, value="d7"),
        )
        properties = _tool_fields_schema(config)["properties"]
        assert "dateRestrict" in properties
        assert "date_restrict" not in properties

    @pytest.mark.ai
    def test_brave_literal_enum_exposed_fields_emit_enum_schema(self) -> None:
        config = BraveConfig(
            country=ExposableCountry(expose=True, value="US"),
            searchLang=ExposableSearchLang(expose=True, value="en"),
        )
        schema = _tool_fields_schema(config)
        country_string = schema["properties"]["country"]["anyOf"][0]
        assert country_string["type"] == "string"
        assert "enum" in country_string
        assert "US" in country_string["enum"]
        search_lang_string = schema["properties"]["searchLang"]["anyOf"][0]
        assert "enum" in search_lang_string
        assert "en" in search_lang_string["enum"]
