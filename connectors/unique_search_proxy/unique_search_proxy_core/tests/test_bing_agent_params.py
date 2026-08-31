"""Bing agent exposable knobs: derived surfaces, merge, and agent naming."""

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
    BingMarketConfig,
    BingMarketSelection,
    ExposableFreshness,
    ExposableSetLang,
)
from unique_search_proxy_core.agent_engines.bing.settings import (
    MarketSettings,
    _get_settings,
    bing_agent_env_settings,
)
from unique_search_proxy_core.param_policy import ExposedParams


def _patch_market_settings(
    monkeypatch: pytest.MonkeyPatch,
    *,
    default: str | None = None,
    enforce: bool = False,
) -> None:
    monkeypatch.setattr(
        bing_agent_env_settings,
        "market",
        MarketSettings(default=default, enforce=enforce),
    )


class TestBingAgentEnvSettings:
    @pytest.mark.ai
    def test_market_default_reads_environment(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify the Bing market default is loaded from the deployment environment.
        Why this matters: Each client environment must be able to select its own market.
        Setup summary: Set the nested market JSON env var and reload settings.
        """
        monkeypatch.setenv("BING_AGENT_MARKET", '{"default": "fr-CH"}')

        settings = _get_settings()
        assert settings.market.default == "fr-CH"
        assert settings.market.enforce is False

    @pytest.mark.ai
    def test_market_enforce_reads_environment(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "BING_AGENT_MARKET",
            '{"default": "de-CH", "enforce": true}',
        )

        settings = _get_settings()
        assert settings.market.default == "de-CH"
        assert settings.market.enforce is True

    @pytest.mark.ai
    @pytest.mark.parametrize("value", ["", "fr-XX"])
    def test_invalid_market_default_rejects_at_settings_load(
        self,
        value: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify unknown market codes fail when loading deployment settings.
        Why this matters: ``market.default`` is typed as ``BingMarket``; a typo must
            surface at startup instead of being silently ignored.
        Setup summary: Set an invalid default and expect settings construction to fail.
        """
        monkeypatch.setenv("BING_AGENT_MARKET", f'{{"default": "{value}"}}')

        with pytest.raises(ValidationError):
            _get_settings()


class TestBingAgentMarketUiSchema:
    @pytest.mark.ai
    def test_market_json_schema_uses_conditional_standard_controls(self) -> None:
        """
        Purpose: Verify the admin schema encodes the exact dependent control flow.
        Why this matters: RJSF must hide agent control until enabled and hide the
            fixed dropdown while the agent controls the parameter.
        Setup summary: Inspect the nested market definition and each conditional branch.
        """
        schema = BingAgentConfig.model_json_schema()
        market_schema = schema["$defs"]["BingMarketConfig"]

        enabled = market_schema["properties"]["enabled"]
        enabled_branch = market_schema["allOf"][0]
        agent_controlled = enabled_branch["then"]["properties"]["agentControlled"]
        fixed_branch = enabled_branch["then"]["allOf"][0]
        market = fixed_branch["then"]["properties"]["market"]

        assert enabled["title"] == "Enable market parameter"
        assert enabled["type"] == "boolean"
        assert enabled_branch["if"]["properties"]["enabled"]["const"] is True
        assert agent_controlled["title"] == "Agent controlled parameter"
        assert agent_controlled["type"] == "boolean"
        assert fixed_branch["if"]["properties"]["agentControlled"]["const"] is False
        assert market["title"] == "Market"
        assert "BING_AGENT_MARKET" in market["description"]

    @pytest.mark.ai
    def test_market_dropdown_contains_default_and_every_bing_market(self) -> None:
        """
        Purpose: Verify the fixed-market dropdown has one durable default source and all codes.
        Why this matters: Admins must not lose a Bing market or see the sentinel in LLM calls.
        Setup summary: Compare the admin enum definition with the request-market literal.
        """
        schema = BingAgentConfig.model_json_schema()
        choices = schema["$defs"]["BingMarketSelection"]["enum"]

        assert choices[0] == "Default"
        assert set(choices[1:]) == set(get_args(BingMarket))

    @pytest.mark.ai
    def test_market_ui_schema_uses_checkboxes_and_existing_fields(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify generated uiSchema uses only built-in RJSF controls.
        Why this matters: The renderer is external, so unsupported custom metadata would break.
        Setup summary: Generate camel-case uiSchema and inspect market controls and order.
        """
        _patch_market_settings(monkeypatch, default="de-CH", enforce=False)

        market_ui = ui_schema_for_model(
            BingAgentConfig,
            key_transform=camelize,
        )["market"]
        assert market_ui["ui:disabled"] is False
        assert market_ui["enabled"]["ui:widget"] == "checkbox"
        assert market_ui["enabled"]["ui:title"] == "Enable market parameter"
        assert market_ui["agentControlled"]["ui:widget"] == "checkbox"
        assert market_ui["agentControlled"]["ui:title"] == "Agent controlled parameter"
        assert market_ui["market"] == {}
        assert market_ui["ui:order"] == ["enabled", "agentControlled", "market"]

    @pytest.mark.ai
    def test_market_ui_schema_disabled_when_enforced(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _patch_market_settings(monkeypatch, default="de-CH", enforce=True)

        market_ui = ui_schema_for_model(BingAgentConfig)["market"]
        assert market_ui["ui:disabled"] is True
        # The lock is set through the nested JSON var; naming a flat
        # `BING_AGENT_MARKET_*` var here would send admins to a variable
        # `_BingAgentEnvSettings` never reads.
        assert "BING_AGENT_MARKET_ENFORCE" not in market_ui["ui:help"]
        assert "BING_AGENT_MARKET" in market_ui["ui:help"]
        assert "enabled" in market_ui
        assert "agent_controlled" in market_ui
        assert "market" in market_ui


class TestBingAgentMarketEnforcement:
    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("env_default", "expected_value"),
        [("de-CH", "de-CH"), (None, None)],
    )
    def test_validate_market_pins_default_source_when_enforced(
        self,
        env_default: str | None,
        expected_value: str | None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify enforcement ignores admin controls and uses the default source.
        Why this matters: Infra enforcement must work with both configured and omitted defaults.
        Setup summary: Enable enforcement, submit conflicting controls, and inspect policy/runtime.
        """
        _patch_market_settings(monkeypatch, default=env_default, enforce=True)

        config = BingAgentConfig.model_validate(
            {
                "market": {
                    "enabled": False,
                    "agentControlled": True,
                    "market": "fr-CH",
                },
            },
        )
        assert config.market == BingMarketConfig(
            enabled=True,
            agent_controlled=False,
            market=BingMarketSelection.DEFAULT,
        )
        assert config.market.expose is False
        assert config.market.value == expected_value

    @pytest.mark.ai
    def test_default_factory_applies_enforcement_without_submitted_market(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify enforcement also applies when saved config omits the market object.
        Why this matters: Infra policy cannot depend on an admin having touched the control.
        Setup summary: Enable enforcement, construct defaults, and inspect effective state.
        """
        _patch_market_settings(monkeypatch, default="de-CH", enforce=True)

        config = BingAgentConfig()

        assert config.market.enabled is True
        assert config.market.agent_controlled is False
        assert config.market.market is BingMarketSelection.DEFAULT
        assert config.market.value == "de-CH"


class TestBingAgentMarketPolicy:
    @pytest.mark.ai
    def test_disabled_omits_market_even_with_environment_default(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify a disabled market never falls back to the environment.
        Why this matters: The enable checkbox is the authoritative opt-in for this parameter.
        Setup summary: Set an env default, disable market, and merge an empty agent payload.
        """
        _patch_market_settings(monkeypatch, default="de-CH")
        config = BingAgentConfig.model_validate(
            {
                "market": {
                    "enabled": False,
                    "agentControlled": False,
                    "market": "fr-CH",
                },
            },
        )

        assert config.market.value is None
        assert config.exposed_params_model() is None
        assert config.merge({}, query="x").market is None

    @pytest.mark.ai
    def test_agent_controlled_omission_has_no_fallback(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify agent control exposes a code but omission sends no market.
        Why this matters: Agent-controlled state must ignore both hidden and env defaults.
        Setup summary: Enable agent control with defaults present, then merge omitted/explicit values.
        """
        _patch_market_settings(monkeypatch, default="de-CH")
        config = BingAgentConfig.model_validate(
            {
                "market": {
                    "enabled": True,
                    "agentControlled": True,
                },
            },
        )
        exposed = config.exposed_params_model()

        assert config.market.value is None
        assert exposed is not None
        assert set(exposed.model_fields) == {"market"}
        assert config.merge({}, query="x").market is None
        assert config.merge({"market": "fr-CH"}, query="x").market == "fr-CH"

    @pytest.mark.ai
    def test_fixed_market_overrides_environment_default(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify a fixed space market is included on every merged request.
        Why this matters: The fixed dropdown must take precedence over deployment defaults.
        Setup summary: Select a specific market with another env default and merge a request.
        """
        _patch_market_settings(monkeypatch, default="de-CH")
        config = BingAgentConfig.model_validate(
            {
                "market": {
                    "enabled": True,
                    "agentControlled": False,
                    "market": "fr-CH",
                },
            },
        )

        assert config.market.value == "fr-CH"
        assert config.exposed_params_model() is None
        assert config.merge({}, query="x").market == "fr-CH"

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("env_default", "expected_market"),
        [("de-CH", "de-CH"), (None, None)],
    )
    def test_default_selection_resolves_environment_at_config_load(
        self,
        env_default: str | None,
        expected_market: str | None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify Default resolves to the environment or omission.
        Why this matters: An unset deployment default must leave Bing free to infer a market.
        Setup summary: Select Default under set/unset env values and merge a request.
        """
        _patch_market_settings(monkeypatch, default=env_default)
        config = BingAgentConfig.model_validate(
            {
                "market": {
                    "enabled": True,
                    "agentControlled": False,
                    "market": "Default",
                },
            },
        )

        assert config.market.value == expected_market
        assert config.merge({}, query="x").market == expected_market

    @pytest.mark.ai
    def test_default_selection_remains_durable_across_environment_changes(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify serialized config stores Default rather than its resolved market.
        Why this matters: Restarting after an env change must update spaces using Default.
        Setup summary: Serialize under one default, change env, reload, and compare resolution.
        """
        _patch_market_settings(monkeypatch, default="de-CH")
        config = BingAgentConfig.model_validate(
            {
                "market": {
                    "enabled": True,
                    "agentControlled": False,
                    "market": "Default",
                },
            },
        )
        saved = config.model_dump(mode="json", by_alias=True)

        assert saved["market"] == {
            "enabled": True,
            "agentControlled": False,
            "market": "Default",
        }
        assert "de-CH" not in config.model_dump_json(by_alias=True)

        _patch_market_settings(monkeypatch, default="fr-CH")
        reloaded = BingAgentConfig.model_validate(saved)
        assert reloaded.market.value == "fr-CH"

    @pytest.mark.ai
    def test_retired_exposable_shape_is_rejected(self) -> None:
        """
        Purpose: Verify the unreleased legacy market shape is removed cleanly.
        Why this matters: Silently accepting old keys would disable policy unexpectedly.
        Setup summary: Validate the former expose/value object and expect an extra-field error.
        """
        with pytest.raises(ValidationError):
            BingAgentConfig.model_validate(
                {"market": {"expose": True, "value": "fr-CH"}},
            )


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
    def test_market_request_schema_is_plain_optional_code(self) -> None:
        """
        Purpose: Verify the proxy request carries a market code, not admin policy.
        Why this matters: Enable/default controls belong only to saved space config.
        Setup summary: Inspect the request property and its non-null enum branch.
        """
        prop = BingAgentSearchRequest.model_json_schema()["properties"]["market"]
        choices = next(branch["enum"] for branch in prop["anyOf"] if "enum" in branch)

        assert set(choices) == set(get_args(BingMarket))
        assert "Default" not in choices
        assert "enabled" not in prop
        assert "agentControlled" not in prop

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
        """
        Purpose: Verify the knobs only accept values Bing documents.
        Why this matters: Bing ignores unknown values, so a plausible-looking one
            from the LLM would return results that look right while ignoring the
            request — and since these knobs are hashed into the agent name, each
            distinct string would also mint its own Foundry agent version.
        Setup summary: Validate a request per invalid value and expect a rejection.
        """
        with pytest.raises(ValidationError):
            BingAgentSearchRequest.model_validate({"query": "x", field: value})

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
            market=BingMarketConfig(
                enabled=True,
                agent_controlled=True,
                market=BingMarketSelection.DEFAULT,
            ),
            freshness=ExposableFreshness(expose=True, value=None),
            set_lang=ExposableSetLang(expose=False, value="fr"),
        )
        exposed = config.exposed_params_model()
        assert exposed is not None
        assert issubclass(exposed, ExposedParams)
        assert exposed.__name__ == "BingAgentExposedParams"
        assert set(exposed.model_fields) == {"market", "freshness"}

    @pytest.mark.ai
    def test_schema_is_description_only(self) -> None:
        config = BingAgentConfig(
            market=BingMarketConfig(
                enabled=True,
                agent_controlled=True,
                market=BingMarketSelection.DEFAULT,
            ),
        )
        exposed = config.exposed_params_model()
        assert exposed is not None
        prop = exposed.model_json_schema()["properties"]["market"]
        assert "Bing `mkt`" in prop["description"]
        # Pydantic auto-title and the admin default must not leak to the LLM.
        assert "title" not in prop
        assert "default" not in prop

    @pytest.mark.ai
    def test_market_choices_reach_the_llm_schema(self) -> None:
        """
        Purpose: Verify the LLM sees Bing's market vocabulary, not a free-form string.
        Why this matters: An unconstrained string invites plausible-looking codes
            such as `fr-XX`, which Bing ignores while still returning results.
        Setup summary: Expose market and inspect the enum branch of its schema.
        """
        config = BingAgentConfig(
            market=BingMarketConfig(
                enabled=True,
                agent_controlled=True,
                market=BingMarketSelection.DEFAULT,
            ),
        )
        exposed = config.exposed_params_model()
        assert exposed is not None
        prop = exposed.model_json_schema()["properties"]["market"]
        choices = next(branch["enum"] for branch in prop["anyOf"] if "enum" in branch)
        assert {"de-CH", "fr-CH", "en-US"} <= set(choices)
        assert "fr-XX" not in choices
        assert "Default" not in choices
        assert "enabled" not in prop
        assert "agentControlled" not in prop


class TestBingAgentMerge:
    @pytest.mark.ai
    def test_admin_defaults_merged(self) -> None:
        config = BingAgentConfig(
            market=BingMarketConfig(
                enabled=True,
                agent_controlled=False,
                market=BingMarketSelection.FR_CH,
            ),
            freshness=ExposableFreshness(expose=False, value="Week"),
        )
        request = config.merge({}, query="x")
        assert isinstance(request, BingAgentSearchRequest)
        assert request.market == "fr-CH"
        assert request.freshness == "Week"

    @pytest.mark.ai
    def test_deactivated_knob_dropped(self) -> None:
        config = BingAgentConfig(
            market=BingMarketConfig(
                enabled=False,
                agent_controlled=False,
                market=BingMarketSelection.DEFAULT,
            ),
        )
        assert config.merge({}, query="x").market is None

    @pytest.mark.ai
    def test_override_wins_over_admin_default(self) -> None:
        config = BingAgentConfig(
            market=BingMarketConfig(
                enabled=True,
                agent_controlled=True,
                market=BingMarketSelection.DEFAULT,
            ),
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
