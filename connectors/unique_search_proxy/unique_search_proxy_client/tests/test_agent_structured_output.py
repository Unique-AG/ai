from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from unique_search_proxy_client.web.core.agent_engines.structured_output import (
    build_agent_instructions,
    build_json_output_format_rule,
)
from unique_search_proxy_client.web.core.agent_engines.vertexai.gemini import (
    build_generate_content_config,
)


class _SampleOutput(BaseModel):
    answer: str = Field(description="Final answer text.")


class TestStructuredOutput:
    @pytest.mark.unit
    def test_build_json_output_format_rule_includes_schema(self) -> None:
        rule = build_json_output_format_rule(_SampleOutput)
        assert "JSON Schema" in rule
        assert '"answer"' in rule

    @pytest.mark.unit
    def test_build_agent_instructions_merges_generation_and_schema(self) -> None:
        instructions = build_agent_instructions(
            generation_instructions="Research the topic.",
            output_schema=_SampleOutput,
        )
        assert instructions.startswith("Research the topic.")
        assert "JSON Schema" in instructions

    @pytest.mark.unit
    def test_vertex_config_sets_structured_output_fields(self) -> None:
        config = build_generate_content_config(
            generation_instructions="Research the topic.",
            output_schema=_SampleOutput,
        )
        assert config.response_mime_type == "application/json"
        assert config.response_schema is _SampleOutput
