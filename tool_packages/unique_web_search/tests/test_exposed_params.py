"""Tests for flat engine-exposed parameter injection (V1 and V3)."""

import pytest
from unique_search_proxy_core.search_engines.call_schema import (
    build_exposed_tool_field_defs,
)
from unique_search_proxy_core.search_engines.google.schema import (
    ExposableStrOrNone,
    GoogleConfig,
)

from unique_web_search.services.executors.exposed_params import (
    collect_flat_exposed_params,
)
from unique_web_search.services.executors.v1.schema import WebSearchToolParameters
from unique_web_search.services.executors.v3.schema import (
    SearchPayload,
    WebSearchV3ToolParameters,
)


class TestV1FlatExposedParams:
    @pytest.mark.ai
    def test_v1_tool_schema_includes_flat_exposed_fields(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="us"),
        )
        field_defs = build_exposed_tool_field_defs(config)
        tool_model = WebSearchToolParameters.with_exposed_fields(
            field_defs,
            query_description="Search query",
        )
        assert "gl" in tool_model.model_fields
        assert "parameters" not in tool_model.model_fields

    @pytest.mark.ai
    def test_v1_tool_schema_has_no_legacy_date_restrict_without_exposure(self) -> None:
        config = GoogleConfig()
        field_defs = build_exposed_tool_field_defs(config)
        tool_model = WebSearchToolParameters.with_exposed_fields(
            field_defs,
            query_description="Search query",
        )
        assert "date_restrict" not in tool_model.model_fields


class TestV3FlatExposedParams:
    @pytest.mark.ai
    def test_search_payload_includes_flat_exposed_fields(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="us"),
        )
        field_defs = build_exposed_tool_field_defs(config)
        payload_model = SearchPayload.with_exposed_fields(field_defs)
        assert "gl" in payload_model.model_fields
        assert "parameters" not in payload_model.model_fields

    @pytest.mark.ai
    def test_search_payload_unchanged_when_nothing_exposed(self) -> None:
        config = GoogleConfig()
        field_defs = build_exposed_tool_field_defs(config)
        assert field_defs is None
        assert SearchPayload.with_exposed_fields(field_defs) is SearchPayload

    @pytest.mark.ai
    def test_v3_tool_schema_has_no_parameters_key(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="us"),
            date_restrict=ExposableStrOrNone(expose=True, value="d7"),
        )
        field_defs = build_exposed_tool_field_defs(config)
        tool_model = WebSearchV3ToolParameters.with_exposed_fields(field_defs)
        schema = tool_model.model_json_schema()
        payload_props = schema["$defs"]["SearchPayload"]["properties"]
        assert "parameters" not in payload_props
        assert "gl" in payload_props
        # Exposed to the LLM under the camelCase alias, not the snake_case name.
        assert "dateRestrict" in payload_props
        assert "date_restrict" not in payload_props
        assert "title" not in payload_props["gl"]
        assert "default" not in payload_props["gl"]

    @pytest.mark.ai
    def test_collect_flat_exposed_params_omits_none(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="us"),
            date_restrict=ExposableStrOrNone(expose=True, value="d7"),
        )
        field_defs = build_exposed_tool_field_defs(config)
        PayloadModel = SearchPayload.with_exposed_fields(field_defs)
        payload = PayloadModel(gap="facet", query="q", gl="ch")
        params = collect_flat_exposed_params(payload)
        assert params == {"gl": "ch"}
