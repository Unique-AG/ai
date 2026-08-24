"""Bing agent exposable knobs: derived surfaces, merge, and agent naming."""

import pytest
from pydantic import ValidationError

from unique_search_proxy_core.agent_engines.base import AgentEngineType
from unique_search_proxy_core.agent_engines.bing.grounding import (
    BING_AUTO_AGENT_NAME_PREFIX,
    BingGroundingConfiguration,
    bing_agent_name,
    is_auto_provisioned_bing_agent_name,
)
from unique_search_proxy_core.agent_engines.bing.schema import (
    BingAgentConfig,
    BingAgentSearchRequest,
    ExposableFreshness,
    ExposableStrOrNone,
)
from unique_search_proxy_core.param_policy import ExposedParams


class TestBingAgentRequestModel:
    @pytest.mark.ai
    def test_exposable_knobs_are_optional_request_fields(self) -> None:
        assert {"market", "set_lang", "freshness"} <= set(
            BingAgentSearchRequest.model_fields,
        )
        request = BingAgentSearchRequest.model_validate({"query": "x"})
        assert request.market is None
        assert request.set_lang is None
        assert request.freshness is None

    @pytest.mark.ai
    def test_camel_case_aliases_accepted(self) -> None:
        request = BingAgentSearchRequest.model_validate(
            {"query": "x", "setLang": "fr", "market": "fr-CH"},
        )
        assert request.set_lang == "fr"
        assert request.market == "fr-CH"

    @pytest.mark.ai
    @pytest.mark.parametrize(
        "freshness", ["Day", "Week", "Month", "2026-01-01..2026-02-01"]
    )
    def test_freshness_accepts_presets_and_ranges(self, freshness: str) -> None:
        request = BingAgentSearchRequest.model_validate(
            {"query": "x", "freshness": freshness},
        )
        assert request.freshness == freshness

    @pytest.mark.ai
    def test_output_schema_is_not_a_request_field(self) -> None:
        assert "output_schema" not in BingAgentSearchRequest.model_fields


class TestBingAgentExposedParams:
    @pytest.mark.ai
    def test_none_when_nothing_exposed(self) -> None:
        assert BingAgentConfig().exposed_params_model() is None

    @pytest.mark.ai
    def test_contains_exactly_the_exposed_knobs(self) -> None:
        config = BingAgentConfig(
            market=ExposableStrOrNone(expose=True, value=None),
            freshness=ExposableFreshness(expose=True, value=None),
            set_lang=ExposableStrOrNone(expose=False, value="fr"),
        )
        exposed = config.exposed_params_model()
        assert exposed is not None
        assert issubclass(exposed, ExposedParams)
        assert exposed.__name__ == "BingAgentExposedParams"
        assert set(exposed.model_fields) == {"market", "freshness"}

    @pytest.mark.ai
    def test_schema_is_description_only(self) -> None:
        config = BingAgentConfig(
            market=ExposableStrOrNone(expose=True, value="en-US"),
        )
        exposed = config.exposed_params_model()
        assert exposed is not None
        prop = exposed.model_json_schema()["properties"]["market"]
        assert "Bing `mkt`" in prop["description"]
        # Pydantic auto-title and the admin default must not leak to the LLM.
        assert "title" not in prop
        assert "default" not in prop


class TestBingAgentMerge:
    @pytest.mark.ai
    def test_admin_defaults_merged(self) -> None:
        config = BingAgentConfig(
            market=ExposableStrOrNone(expose=False, value="fr-CH"),
            freshness=ExposableFreshness(expose=False, value="Week"),
        )
        request = config.merge({}, query="x")
        assert isinstance(request, BingAgentSearchRequest)
        assert request.market == "fr-CH"
        assert request.freshness == "Week"

    @pytest.mark.ai
    def test_deactivated_knob_dropped(self) -> None:
        config = BingAgentConfig(market=ExposableStrOrNone(expose=True, value=None))
        assert config.merge({}, query="x").market is None

    @pytest.mark.ai
    def test_override_wins_over_admin_default(self) -> None:
        config = BingAgentConfig(
            market=ExposableStrOrNone(expose=True, value="en-US"),
        )
        assert config.merge({"market": "fr-CH"}, query="x").market == "fr-CH"

    @pytest.mark.ai
    def test_engine_injected_from_config(self) -> None:
        assert BingAgentConfig().merge({}, query="x").engine == AgentEngineType.BING

    @pytest.mark.ai
    def test_invalid_override_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BingAgentConfig().merge({"fetch_size": 0}, query="x")


class TestBingAgentNaming:
    @pytest.mark.ai
    def test_name_is_stable_and_recognized(self) -> None:
        grounding = BingGroundingConfiguration(fetch_size=5, market="fr-CH")
        name = bing_agent_name(
            model="gpt-5.1", instructions="Be helpful.", grounding=grounding
        )
        assert name.startswith(f"{BING_AUTO_AGENT_NAME_PREFIX}-")
        assert is_auto_provisioned_bing_agent_name(name)
        assert name == bing_agent_name(
            model="gpt-5.1", instructions="Be helpful.", grounding=grounding
        )

    @pytest.mark.ai
    @pytest.mark.parametrize(
        "knob",
        [
            {"fetch_size": 10},
            {"market": "fr-CH"},
            {"set_lang": "fr"},
            {"freshness": "Week"},
        ],
    )
    def test_every_knob_changes_the_name(self, knob: dict[str, object]) -> None:
        """
        Purpose: Verify each tool knob participates in the agent name hash.
        Why this matters: Knobs are baked into the agent version at creation time,
            so a shared name would silently serve a differently configured agent.
        Setup summary: Compare a baseline name against one changed knob at a time.
        """
        base = BingGroundingConfiguration(fetch_size=5)
        changed = BingGroundingConfiguration(**{"fetch_size": 5, **knob})
        assert bing_agent_name(
            model="gpt-5.1", instructions="i", grounding=base
        ) != bing_agent_name(model="gpt-5.1", instructions="i", grounding=changed)

    @pytest.mark.ai
    def test_foreign_names_are_not_auto_provisioned(self) -> None:
        assert not is_auto_provisioned_bing_agent_name("my-own-agent")
