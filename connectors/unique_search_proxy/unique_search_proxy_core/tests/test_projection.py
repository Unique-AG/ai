import pytest
from pydantic import BaseModel, Field

from unique_search_proxy_core.param_policy.resolver import (
    project_non_strict,
    project_strict,
)
from unique_search_proxy_core.schema import camelized_model_config


class SampleCallSchema(BaseModel):
    model_config = camelized_model_config

    query: str
    fetch_size: int = Field(default=10, ge=1, le=100)
    secret_flag: bool = False


class TestProjection:
    @pytest.mark.ai
    def test_project_exposes_subset(self) -> None:
        projected = project_non_strict(SampleCallSchema, ["query", "fetchSize"])
        instance = projected.model_validate({"query": "hello", "fetchSize": 5})
        assert instance.query == "hello"
        assert instance.fetch_size == 5
        assert "secret_flag" not in projected.model_fields

    @pytest.mark.ai
    def test_strict_projection_makes_fields_required(self) -> None:
        projected = project_strict(SampleCallSchema, ["query", "fetchSize"])
        schema = projected.model_json_schema()
        assert set(schema["required"]) == {"query", "fetchSize"}

    @pytest.mark.ai
    def test_unknown_field_raises(self) -> None:
        with pytest.raises(ValueError, match="not defined"):
            project_non_strict(SampleCallSchema, ["missing"])

    @pytest.mark.ai
    def test_empty_exposed_fields_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one"):
            project_non_strict(SampleCallSchema, [])

    @pytest.mark.ai
    def test_projected_json_schema_contains_only_exposed_fields(self) -> None:
        schema = project_non_strict(SampleCallSchema, ["query"]).model_json_schema()
        properties = schema.get("properties", {})
        assert "query" in properties
        assert "secretFlag" not in properties
