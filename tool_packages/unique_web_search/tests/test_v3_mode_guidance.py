"""Tests for search-engine-mode-aware WebSearch V3 query guidance."""

import json
from importlib.resources import files

import pytest
from pydantic import BaseModel
from unique_search_proxy_core.search_engines.google.schema import GoogleConfig

from unique_web_search.services.executors.modes import WebSearchToolContext
from unique_web_search.services.executors.v3.config import WebSearchV3Config
from unique_web_search.services.executors.v3.schema import WebSearchV3ToolParameters
from unique_web_search.services.executors.v3.strategy import WebSearchV3Strategy
from unique_web_search.services.search_engine.base import SearchEngineMode
from unique_web_search.services.search_engine.bing import BingSearchConfig
from unique_web_search.services.search_engine.custom_api import CustomAPIConfig
from unique_web_search.services.search_engine.vertexai import VertexAIConfig


def _tool_context(
    search_engine_config: BaseModel,
) -> WebSearchToolContext:
    exposed_params_factory = getattr(search_engine_config, "exposed_params_model", None)
    return WebSearchToolContext(
        search_engine_config=search_engine_config,
        date_string="Saturday August 29, 2026",
        exposed_params_cls=(
            exposed_params_factory() if callable(exposed_params_factory) else None
        ),
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
        system_prompt = strategy.system_prompt(context)

        assert _query_description(parameters_model) == (
            "Short search-engine keyword line (~3–8 words, not a sentence). "
            "Do not pack multiple facets into one query—issue parallel `search` calls "
            "with one `gap` each instead. Do not paste the user question or `gap` text "
            "here."
        )
        assert "3–8 words" in tool_description
        assert "short `query` each, not one long query" in tool_description
        assert "~3–8 keywords only" in system_prompt
        assert "one short `query` per call" in system_prompt

    @pytest.mark.ai
    @pytest.mark.parametrize(
        "search_engine_config",
        [
            BingSearchConfig(),
            VertexAIConfig(),
            CustomAPIConfig(search_engine_mode=SearchEngineMode.AGENT),
        ],
        ids=["bing", "vertex-ai", "custom-api-agent"],
    )
    def test_agent_mode_uses_comprehensive_intent_guidance(
        self,
        search_engine_config: BaseModel,
    ) -> None:
        """
        Purpose: Verify V3 gives agent engines a complete natural-language research request.
        Why this matters: Agent engines plan searches internally and lose context in terse keywords.
        Setup summary: Build each agent engine's surfaces, then reject short-query wording.
        """
        strategy = WebSearchV3Strategy(WebSearchV3Config())
        context = _tool_context(search_engine_config)

        parameters_model = strategy.build_tool_parameters(context)
        model_json_schema = parameters_model.model_json_schema()
        parameter_schema = json.dumps(model_json_schema)
        tool_description = strategy.tool_description(context)
        system_prompt = strategy.system_prompt(context)

        assert "comprehensive natural-language research request" in _query_description(
            parameters_model
        )
        assert "full intent, context, and constraints" in _query_description(
            parameters_model
        )
        assert "comprehensive natural-language research request" in tool_description
        assert "3–8 words" not in parameter_schema
        assert "precise, short" not in parameter_schema
        assert (
            "pursue the research request"
            in model_json_schema["properties"]["phase"]["description"]
        )
        assert "3–8 words" not in tool_description
        assert "short `query`" not in tool_description
        assert "comprehensive natural-language research request" in system_prompt
        assert "full intent, context, and constraints" in system_prompt
        assert "3–8" not in system_prompt
        assert "short `payload.query`" not in system_prompt
        assert "short `query`" not in system_prompt

    @pytest.mark.ai
    def test_agent_mode_does_not_expose_fixed_bing_parameters(self) -> None:
        """
        Purpose: Verify fixed Bing parameters stay out of the assistant tool schema.
        Why this matters: Space-level values cannot be changed by the assistant.
        Setup summary: Set a Bing market, build V3 parameters, and inspect the payload.
        """
        config = BingSearchConfig(market="fr-CH")
        strategy = WebSearchV3Strategy(WebSearchV3Config())

        parameters_model = strategy.build_tool_parameters(_tool_context(config))
        payload_properties = parameters_model.model_json_schema()["$defs"][
            "SearchPayload"
        ]["properties"]

        assert "market" not in payload_properties
        assert (
            "comprehensive natural-language research request"
            in payload_properties["query"]["description"]
        )

    @pytest.mark.ai
    def test_bundled_skill_defers_query_shape_to_live_schema(self) -> None:
        """
        Purpose: Ensure the optional V3 skill cannot override engine-specific guidance.
        Why this matters: The skill is activated for complex searches in every engine mode.
        Setup summary: Read the packaged skill and verify it describes both live-schema branches.
        """
        skill_text = (
            files("unique_web_search")
            .joinpath("skills/web-search-v3.md")
            .read_text(encoding="utf-8")
        )

        assert "Follow the live tool schema" in skill_text
        assert "**Standard engine**" in skill_text
        assert "**Agent engine**" in skill_text
        assert "do not condense it into keywords" in skill_text
        assert "payload.query` to one focused 3-8 keyword string" not in skill_text
