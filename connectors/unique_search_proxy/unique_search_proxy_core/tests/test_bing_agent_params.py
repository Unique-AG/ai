"""Bing grounding configuration, request validation, merge, and agent naming."""

import json
from typing import get_args

import pytest
from humps import camelize
from pydantic import ValidationError
from unique_toolkit._common.pydantic.rjsf_tags import ui_schema_for_model

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
    BingMarket,
)


class TestBingAgentAdminConfig:
    @pytest.mark.ai
    def test_optional_fields_have_simple_admin_controls(self) -> None:
        """
        Purpose: Verify Bing's optional settings render as plain fixed values.
        Why this matters: The form must not imply assistant control or show union selectors.
        Setup summary: Inspect the admin JSON schema and freshness uiSchema.
        """
        schema = BingAgentConfig.model_json_schema()
        properties = schema["properties"]
        ui_schema = ui_schema_for_model(BingAgentConfig, key_transform=camelize)

        market = properties["market"]
        assert market["oneOf"][0] == {"const": None, "title": "No fixed market"}
        assert {choice["const"] for choice in market["oneOf"][1:]} == set(
            get_args(BingMarket)
        )
        assert market["type"] == ["string", "null"]
        assert "anyOf" not in market

        set_lang = properties["setLang"]
        assert set_lang["oneOf"][0] == {
            "const": None,
            "title": "No fixed interface language",
        }
        assert set_lang["type"] == ["string", "null"]
        assert "anyOf" not in set_lang

        freshness = properties["freshness"]
        assert freshness["type"] == ["string", "null"]
        assert "anyOf" not in freshness
        assert "pattern" not in freshness
        assert ui_schema["freshness"]["ui:widget"] == "text"
        assert ui_schema["freshness"]["ui:emptyValue"] is None

        serialized = json.dumps(schema)
        assert "fixedMarket" not in serialized
        assert "fixedLanguage" not in serialized
        assert "fixedFreshness" not in serialized
        assert '"enabled"' not in serialized

    @pytest.mark.ai
    def test_defaults_omit_all_optional_bing_parameters(self) -> None:
        saved = BingAgentConfig().model_dump(mode="json", by_alias=True)
        assert saved["market"] is None
        assert saved["setLang"] is None
        assert saved["freshness"] is None
        assert BingAgentConfig().exposed_params_model() is None

    @pytest.mark.ai
    def test_fixed_values_are_merged_into_every_request(self) -> None:
        config = BingAgentConfig(
            market="fr-CH",
            set_lang="fr",
            freshness="Week",
        )

        request = config.merge({}, query="x")

        assert isinstance(request, BingAgentSearchRequest)
        assert request.market == "fr-CH"
        assert request.set_lang == "fr"
        assert request.freshness == "Week"
        assert config.exposed_params_model() is None

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("market", {"enabled": True, "fixedMarket": True, "market": "fr-CH"}),
            ("setLang", {"expose": False, "value": "fr"}),
            (
                "freshness",
                {"enabled": True, "fixedFreshness": True, "freshness": "Week"},
            ),
        ],
    )
    def test_retired_wrapper_shapes_are_rejected(
        self,
        field: str,
        value: dict[str, object],
    ) -> None:
        with pytest.raises(ValidationError):
            BingAgentConfig.model_validate({field: value})

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("market", "fr-XX"),
            ("setLang", "ja"),
            ("freshness", "recently"),
            ("freshness", "2026-"),
        ],
    )
    def test_invalid_fixed_values_are_rejected_on_save(
        self,
        field: str,
        value: str,
    ) -> None:
        with pytest.raises(ValidationError):
            BingAgentConfig.model_validate({field: value})


class TestBingAgentRequestModel:
    @pytest.mark.ai
    def test_optional_bing_fields_are_request_fields(self) -> None:
        assert {"market", "set_lang", "freshness"} <= set(
            BingAgentSearchRequest.model_fields,
        )
        request = BingAgentSearchRequest.model_validate({"query": "x"})
        assert request.market is None
        assert request.set_lang is None
        assert request.freshness is None

    @pytest.mark.ai
    def test_camel_case_aliases_are_accepted(self) -> None:
        request = BingAgentSearchRequest.model_validate(
            {"query": "x", "setLang": "fr", "market": "fr-CH"},
        )
        assert request.set_lang == "fr"
        assert request.market == "fr-CH"

    @pytest.mark.ai
    def test_market_request_schema_remains_strict(self) -> None:
        prop = BingAgentSearchRequest.model_json_schema()["properties"]["market"]
        choices = next(branch["enum"] for branch in prop["anyOf"] if "enum" in branch)

        assert set(choices) == set(get_args(BingMarket))
        assert "Default" not in choices

    @pytest.mark.ai
    @pytest.mark.parametrize(
        "freshness",
        ["Day", "Week", "Month", "2026-02-04", "2026-01-01..2026-02-01"],
    )
    def test_freshness_accepts_presets_days_and_ranges(self, freshness: str) -> None:
        request = BingAgentSearchRequest.model_validate(
            {"query": "x", "freshness": freshness},
        )
        assert request.freshness == freshness

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("market", "fr-XX"),
            ("market", "french"),
            ("market", "fr"),
            ("setLang", "ja"),
            ("freshness", "recently"),
            ("freshness", "day"),
            ("freshness", "last week"),
            ("freshness", "2026-01-01-2026-02-01"),
        ],
    )
    def test_values_outside_bings_vocabulary_are_rejected(
        self,
        field: str,
        value: str,
    ) -> None:
        with pytest.raises(ValidationError):
            BingAgentSearchRequest.model_validate({"query": "x", field: value})

    @pytest.mark.ai
    def test_output_schema_is_not_a_request_field(self) -> None:
        assert "output_schema" not in BingAgentSearchRequest.model_fields


class TestBingAgentMerge:
    @pytest.mark.ai
    def test_blank_values_are_dropped(self) -> None:
        request = BingAgentConfig().merge({}, query="x")
        assert request.market is None
        assert request.set_lang is None
        assert request.freshness is None

    @pytest.mark.ai
    def test_engine_is_injected_from_config(self) -> None:
        assert BingAgentConfig().merge({}, query="x").engine == AgentEngineType.BING

    @pytest.mark.ai
    def test_invalid_override_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BingAgentConfig().merge({"fetch_size": 0}, query="x")


class TestBingAgentNaming:
    @pytest.mark.ai
    def test_name_is_stable_and_recognized(self) -> None:
        grounding = BingGroundingConfiguration(fetch_size=5, market="fr-CH")
        name = bing_agent_name(
            model="gpt-5.1",
            instructions="Be helpful.",
            grounding=grounding,
        )
        assert name.startswith(f"{BING_AUTO_AGENT_NAME_PREFIX}-")
        assert is_auto_provisioned_bing_agent_name(name)
        assert name == bing_agent_name(
            model="gpt-5.1",
            instructions="Be helpful.",
            grounding=grounding,
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
        base = BingGroundingConfiguration(fetch_size=5)
        changed = BingGroundingConfiguration(**{"fetch_size": 5, **knob})
        assert bing_agent_name(
            model="gpt-5.1",
            instructions="i",
            grounding=base,
        ) != bing_agent_name(
            model="gpt-5.1",
            instructions="i",
            grounding=changed,
        )

    @pytest.mark.ai
    def test_foreign_names_are_not_auto_provisioned(self) -> None:
        assert not is_auto_provisioned_bing_agent_name("my-own-agent")
