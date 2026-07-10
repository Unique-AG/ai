"""LLM-facing exposed-params model derivation and inheritance contract."""

import pytest
from pydantic import BaseModel, Field, create_model

from unique_search_proxy_core.param_policy import ExposedParams
from unique_search_proxy_core.search_engines.brave.schema import (
    BraveConfig,
    ExposableCountry,
)
from unique_search_proxy_core.search_engines.google.schema import (
    ExposableStrOrNone,
    GoogleConfig,
)


def _google_config(**exposed: bool) -> GoogleConfig:
    fields = {
        name: ExposableStrOrNone(expose=expose, value=None)
        for name, expose in exposed.items()
    }
    return GoogleConfig(**fields)


class TestExposedParamsModel:
    @pytest.mark.ai
    def test_none_when_nothing_exposed(self) -> None:
        assert GoogleConfig().exposed_params_model() is None

    @pytest.mark.ai
    def test_contains_exactly_the_exposed_fields(self) -> None:
        config = _google_config(date_restrict=True, gl=True, hl=False)
        exposed = config.exposed_params_model()
        assert exposed is not None
        assert set(exposed.model_fields) == {"date_restrict", "gl"}
        assert issubclass(exposed, ExposedParams)
        assert exposed.__name__ == "GoogleExposedParams"

    @pytest.mark.ai
    def test_camel_case_aliases(self) -> None:
        config = _google_config(date_restrict=True)
        exposed = config.exposed_params_model()
        assert exposed is not None
        assert exposed.model_fields["date_restrict"].alias == "dateRestrict"
        instance = exposed.model_validate({"dateRestrict": "d7"})
        assert instance.date_restrict == "d7"

    @pytest.mark.ai
    def test_schema_is_description_only(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=True, value="d7"),
        )
        exposed = config.exposed_params_model()
        assert exposed is not None
        schema = exposed.model_json_schema()
        prop = schema["properties"]["dateRestrict"]
        assert "Recency filter" in prop["description"]
        # Pydantic auto-title and the admin default must not leak to the LLM.
        assert "title" not in prop
        assert "default" not in prop

    @pytest.mark.ai
    def test_literal_enum_surfaces_inline(self) -> None:
        config = BraveConfig(country=ExposableCountry(expose=True, value="US"))
        exposed = config.exposed_params_model()
        assert exposed is not None
        prop = exposed.model_json_schema()["properties"]["country"]
        assert "CH" in prop["anyOf"][0]["enum"]

    @pytest.mark.ai
    def test_all_fields_optional(self) -> None:
        config = _google_config(date_restrict=True, gl=True)
        exposed = config.exposed_params_model()
        assert exposed is not None
        instance = exposed.model_validate({})
        assert instance.date_restrict is None
        assert instance.gl is None


class TestToolModelInheritance:
    """The PR-3 consumption contract: graft knobs via ordinary inheritance."""

    @pytest.mark.ai
    def test_create_model_merge_onto_tool_base(self) -> None:
        config = _google_config(date_restrict=True)
        exposed = config.exposed_params_model()
        assert exposed is not None

        class ToolParamsBase(BaseModel):
            query: str = Field(description="What to search for")

        combined = create_model(
            "WebSearchToolParameters",
            __base__=(ToolParamsBase, exposed),
        )
        parameters = combined.model_validate({"query": "x", "dateRestrict": "m1"})
        assert parameters.query == "x"
        assert parameters.date_restrict == "m1"

    @pytest.mark.ai
    def test_combined_schema_inherits_noise_stripping(self) -> None:
        config = _google_config(date_restrict=True)
        exposed = config.exposed_params_model()
        assert exposed is not None

        class ToolParamsBase(BaseModel):
            query: str = Field(description="What to search for")

        combined = create_model("ToolParams", __base__=(ToolParamsBase, exposed))
        schema = combined.model_json_schema()
        assert schema["required"] == ["query"]
        for prop in schema["properties"].values():
            assert "title" not in prop
            assert "default" not in prop

    @pytest.mark.ai
    def test_exposed_field_names_are_just_model_fields(self) -> None:
        config = _google_config(date_restrict=True, gl=True)
        exposed = config.exposed_params_model()
        assert exposed is not None
        assert sorted(exposed.model_fields) == ["date_restrict", "gl"]
