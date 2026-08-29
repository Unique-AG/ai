"""Tests for search-engine-mode-aware WebSearch V3 query guidance."""

import json

import pytest
from unique_search_proxy_core.search_engines.google.schema import GoogleConfig

from unique_web_search.services.executors.modes import WebSearchToolContext
from unique_web_search.services.executors.v3.config import WebSearchV3Config
from unique_web_search.services.executors.v3.schema import WebSearchV3ToolParameters
from unique_web_search.services.executors.v3.strategy import WebSearchV3Strategy
from unique_web_search.services.search_engine.bing import BingSearchConfig


def _tool_context(
    search_engine_config: GoogleConfig | BingSearchConfig,
) -> WebSearchToolContext:
    return WebSearchToolContext(
        search_engine_config=search_engine_config,
        date_string="Saturday August 29, 2026",
        exposed_params_cls=search_engine_config.exposed_params_model(),
    )


def _query_description(
    parameters_model: type[WebSearchV3ToolParameters],
) -> str:
    schema = parameters_model.model_json_schema()
    return schema["$defs"]["SearchPayload"]["properties"]["query"]["description"]


class TestV3ModeGuidance:
    @pytest.mark.ai
    def test_standard_mode_preserves_short_keyword_guidance(self) -> None:
        """
        Purpose: Verify V3 keeps its existing concise query instructions for standard engines.
        Why this matters: Traditional search engines perform best with focused keyword queries.
        Setup summary: Build Google parameters and description, then inspect both surfaces.
        """
        strategy = WebSearchV3Strategy(WebSearchV3Config())
        context = _tool_context(GoogleConfig())

        parameters_model = strategy.build_tool_parameters(context)
        tool_description = strategy.tool_description(context)

        assert _query_description(parameters_model) == (
            "Short search-engine keyword line (~3–8 words, not a sentence). "
            "Do not pack multiple facets into one query—issue parallel `search` calls "
            "with one `gap` each instead. Do not paste the user question or `gap` text "
            "here."
        )
        assert "3–8 words" in tool_description
        assert "short `query` each, not one long query" in tool_description

    @pytest.mark.ai
    def test_agent_mode_uses_comprehensive_intent_guidance(self) -> None:
        """
        Purpose: Verify V3 gives agent engines a complete natural-language research request.
        Why this matters: Agent engines plan searches internally and lose context in terse keywords.
        Setup summary: Build Bing parameters and description, then reject all short-query wording.
        """
        strategy = WebSearchV3Strategy(WebSearchV3Config())
        context = _tool_context(BingSearchConfig())

        parameters_model = strategy.build_tool_parameters(context)
        parameter_schema = json.dumps(parameters_model.model_json_schema())
        tool_description = strategy.tool_description(context)

        assert "comprehensive natural-language research request" in _query_description(
            parameters_model
        )
        assert "full intent, context, and constraints" in _query_description(
            parameters_model
        )
        assert "comprehensive natural-language research request" in tool_description
        assert "3–8 words" not in parameter_schema
        assert "precise, short" not in parameter_schema
        assert "3–8 words" not in tool_description
        assert "short `query`" not in tool_description

    @pytest.mark.ai
    def test_agent_mode_preserves_exposed_engine_parameters(self) -> None:
        """
        Purpose: Verify mode-specific payload generation retains exposed engine controls.
        Why this matters: Tailored guidance must not remove admin-enabled per-call parameters.
        Setup summary: Expose Bing market, build V3 parameters, and inspect payload properties.
        """
        config = BingSearchConfig.model_validate(
            {"market": {"expose": True, "value": "en-US"}},
        )
        strategy = WebSearchV3Strategy(WebSearchV3Config())

        parameters_model = strategy.build_tool_parameters(_tool_context(config))
        payload_properties = parameters_model.model_json_schema()["$defs"][
            "SearchPayload"
        ]["properties"]

        assert "market" in payload_properties
        assert (
            "comprehensive natural-language research request"
            in payload_properties["query"]["description"]
        )
