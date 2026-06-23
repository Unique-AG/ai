"""Tests for agent-search core schemas and request unions."""

from __future__ import annotations

import pytest

from unique_search_proxy_core.agent_engines.bing.schema import (
    BingAgentConfig,
    BingAgentSearchRequest,
)
from unique_search_proxy_core.agent_engines.config_types import (
    parse_agent_search_request,
)
from unique_search_proxy_core.agent_engines.output_schema import AgentSearchOutput
from unique_search_proxy_core.agent_engines.resolve import (
    resolve_output_schema,
    resolve_output_schema_for_engine,
)
from unique_search_proxy_core.schema import (
    AgentSearchDelta,
    AgentSearchDone,
    AgentSearchResponse,
    ProvidersListResponse,
)


class TestAgentSearchSchemas:
    @pytest.mark.unit
    def test_agent_search_response_minimal(self) -> None:
        response = AgentSearchResponse(
            engine="bing",
            query="hello",
            answer="agent text",
            raw={"threadId": "t1"},
        )
        payload = response.model_dump(by_alias=True)
        assert payload["answer"] == "agent text"
        assert "citations" not in payload

    @pytest.mark.unit
    def test_stream_event_union_delta_and_done(self) -> None:
        delta = AgentSearchDelta(text="chunk")
        assert delta.type == "delta"
        done = AgentSearchDone(
            response=AgentSearchResponse(
                engine="vertexai",
                query="q",
                answer="full",
                raw=None,
            ),
        )
        assert done.type == "done"

    @pytest.mark.unit
    def test_providers_list_includes_agent_engines(self) -> None:
        body = ProvidersListResponse(
            search_engines=["google"],
            agent_engines=["bing", "vertexai"],
            crawlers=["basic"],
        )
        assert body.agent_engines == ["bing", "vertexai"]


class TestAgentSearchRequestUnion:
    @pytest.mark.unit
    def test_parse_bing_request(self) -> None:
        request = parse_agent_search_request(
            {
                "engine": "bing",
                "query": "test query",
                "fetchSize": 3,
                "timeout": 90,
            },
        )
        assert request.engine.value == "bing"  # type: ignore[attr-defined]
        assert request.query == "test query"  # type: ignore[attr-defined]

    @pytest.mark.unit
    def test_parse_vertexai_request(self) -> None:
        request = parse_agent_search_request(
            {
                "engine": "vertexai",
                "query": "test",
                "vertexaiModelName": "gemini-2.0-flash",
                "enableEnterpriseSearch": True,
            },
        )
        assert request.engine.value == "vertexai"  # type: ignore[attr-defined]
        assert request.vertexai_model_name == "gemini-2.0-flash"  # type: ignore[attr-defined]


class TestAgentOutputSchema:
    @pytest.mark.unit
    def test_base_config_defaults_to_agent_search_output(self) -> None:
        config = BingAgentConfig()
        assert config.output_schema is AgentSearchOutput

    @pytest.mark.unit
    def test_output_schema_excluded_from_flat_request(self) -> None:
        assert "output_schema" not in BingAgentSearchRequest.model_fields

    @pytest.mark.unit
    def test_resolve_output_schema_for_engine(self) -> None:
        assert resolve_output_schema(BingAgentConfig) is AgentSearchOutput
        assert resolve_output_schema_for_engine("bing") is AgentSearchOutput
        assert resolve_output_schema_for_engine("vertexai") is AgentSearchOutput

    @pytest.mark.unit
    def test_output_schema_field_hidden_from_json_schema(self) -> None:
        schema = BingAgentConfig.model_json_schema()
        assert "outputSchema" not in schema.get("properties", {})
        assert "output_schema" not in schema.get("properties", {})
