"""Bing agent fixed grounding knobs: admin form, env default, requests, naming."""

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
    BingFreshnessPreset,
    BingMarket,
)
from unique_search_proxy_core.agent_engines.bing.settings import (
    _get_settings,
    bing_agent_env_settings,
    resolve_market,
)


def _patch_default_market(
    monkeypatch: pytest.MonkeyPatch,
    value: str | None,
) -> None:
    monkeypatch.setattr(bing_agent_env_settings, "default_market", value)


class TestBingAgentAdminForm:
    @pytest.mark.ai
    def test_knobs_render_as_one_control_each(self) -> None:
        """
        Purpose: Verify each grounding knob is a single admin control.
        Why this matters: ``Literal | None`` reaches RJSF as an ``anyOf``, which it
            draws as a branch picker ("option 1 / option 2") wrapping a second
            control — the shape that made the first attempt at these knobs
            unusable. Both knobs must be one dropdown each.
        Setup summary: Inspect the admin JSON schema for both properties.
        """
        properties = BingAgentConfig.model_json_schema()["properties"]

        market = properties["searchMarket"]
        assert "anyOf" not in market
        assert market["type"] == ["string", "null"]
        assert market["oneOf"][0] == {"const": None, "title": "Not set"}
        assert {choice["const"] for choice in market["oneOf"][1:]} == set(
            get_args(BingMarket)
        )

        freshness = properties["searchFreshness"]
        assert "anyOf" not in freshness
        assert freshness["type"] == ["string", "null"]
        assert freshness["oneOf"][0] == {"const": None, "title": "Not set"}
        assert {choice["const"] for choice in freshness["oneOf"][1:]} == set(
            get_args(BingFreshnessPreset)
        )

    @pytest.mark.ai
    def test_freshness_options_are_labelled_for_admins(self) -> None:
        """
        Purpose: Verify the recency presets carry admin-facing option labels.
        Why this matters: Bing's wire values are terse enough to be ambiguous —
            "Day" reads as "today" rather than "the last 24 hours" — and the
            dropdown is the only place an admin sees them.
        Setup summary: Inspect the titles on the freshness ``oneOf`` branches.
        """
        freshness = BingAgentConfig.model_json_schema()["properties"]["searchFreshness"]

        assert {choice["const"]: choice["title"] for choice in freshness["oneOf"]} == {
            None: "Not set",
            "Day": "Past 24 hours",
            "Week": "Past 7 days",
            "Month": "Past 30 days",
        }

    @pytest.mark.ai
    def test_no_exposable_wrapper_survives_in_the_schema(self) -> None:
        """
        Purpose: Verify the knobs are plain fixed values, not exposable params.
        Why this matters: These are admin decisions applied to every search; an
            ``{expose, value}`` wrapper would put a checkbox in the form and
            offer the knob to the LLM to steer per call.
        Setup summary: Serialize the admin schema and assert the wrapper is gone.
        """
        serialized = json.dumps(BingAgentConfig.model_json_schema())

        assert '"expose"' not in serialized
        assert "Exposable" not in serialized
        assert BingAgentConfig().exposed_params_model() is None

    @pytest.mark.ai
    def test_knobs_are_visible_in_the_admin_ui_schema(self) -> None:
        """
        Purpose: Verify the knobs are no longer hidden from the admin form.
        Why this matters: 2026.36 shipped them behind ``ui:widget: hidden`` because
            the form was not acceptable. This rework is what releases them, so a
            leftover hidden tag would silently ship nothing.
        Setup summary: Generate the config uiSchema and check for hidden widgets.
        """
        ui_schema = ui_schema_for_model(BingAgentConfig, key_transform=camelize)

        for knob in ("searchMarket", "searchFreshness"):
            assert ui_schema.get(knob, {}).get("ui:widget") != "hidden"

    @pytest.mark.ai
    def test_defaults_leave_every_knob_blank(self) -> None:
        saved = BingAgentConfig().model_dump(mode="json", by_alias=True)

        assert saved["searchMarket"] is None
        assert saved["searchFreshness"] is None


class TestStoredConfigCompatibility:
    """The 2026.36 keys are retired, not reshaped — that is what keeps rollback safe."""

    @pytest.mark.ai
    @pytest.mark.parametrize(
        "legacy",
        [
            {"market": {"expose": False, "value": None}},
            {"market": {"expose": False, "value": "fr-CH"}},
            {"market": {"expose": True, "value": "de-CH"}},
            {"freshness": {"expose": False, "value": "Week"}},
            {"setLang": {"expose": False, "value": "de"}},
            # Not burned keys, but still present on pre-#2263 rows.
            {"agentId": "legacy-agent", "endpoint": "https://old.example.com"},
            {"market": {}, "freshness": {}},
            {"market": None, "freshness": None, "setLang": None},
        ],
    )
    def test_retired_keys_are_ignored_not_reshaped(
        self,
        legacy: dict[str, object],
    ) -> None:
        """
        Purpose: Verify every config key retired on 2026.36 validates as an extra.
        Why this matters: A field reusing one of these names would inherit the
            stale wrapper shape, and ``ToolBuildConfig`` answers an invalid tool
            config by silently disabling the whole tool rather than raising. The
            names are recorded in ``_BURNED_CONFIG_KEYS`` for that reason.
        Setup summary: Validate each retired shape and assert it is dropped.
        """
        config = BingAgentConfig.model_validate(legacy)

        assert config.search_market is None
        assert config.search_freshness is None
        for key in legacy:
            assert key not in config.model_dump(by_alias=True)

    @pytest.mark.ai
    def test_current_keys_are_not_burned_names(self) -> None:
        """
        Purpose: Verify no live field reuses a key retired on an earlier release.
        Why this matters: Reuse is the one way the rename stops protecting us, and
            it would surface as a whole tool silently disabling for spaces saved
            on 2026.36 — not as a validation error anyone would see.
        Setup summary: Compare the config's JSON keys against the burned set.
        """
        keys = {
            field.alias or name for name, field in BingAgentConfig.model_fields.items()
        }

        assert keys.isdisjoint(BingAgentConfig._BURNED_CONFIG_KEYS)

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("payload_key", "attribute"),
        [
            ("searchMarket", "search_market"),
            ("searchFreshness", "search_freshness"),
        ],
    )
    def test_blank_string_is_read_as_blank(
        self,
        payload_key: str,
        attribute: str,
    ) -> None:
        """
        Purpose: Verify a cleared control saves as "no fixed value".
        Why this matters: A cleared dropdown or text input can arrive as ``""``,
            which the Bing vocabularies would reject and turn into a form error
            for a knob the admin was allowed to leave unset.
        Setup summary: Validate each knob as an empty string.
        """
        config = BingAgentConfig.model_validate({payload_key: ""})

        assert getattr(config, attribute) is None


class TestDefaultMarketFromEnvironment:
    @pytest.mark.ai
    def test_default_market_reads_environment(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify the deployment market default is loaded from the environment.
        Why this matters: A deployment serving one country pins its market once
            instead of per space.
        Setup summary: Set the env var and reload settings.
        """
        monkeypatch.setenv("BING_AGENT_DEFAULT_MARKET", "fr-FR")

        assert _get_settings().default_market == "fr-FR"

    @pytest.mark.ai
    @pytest.mark.parametrize("value", ["", "   "])
    def test_blank_default_market_loads_as_unset(
        self,
        value: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify an empty variable does not stop the service from booting.
        Why this matters: Helm renders an unconfigured optional value as ``""``, and
            a ``BingMarket`` literal would reject it — taking down every search to
            enforce an optional knob.
        Setup summary: Set the var to blank and load settings.
        """
        monkeypatch.setenv("BING_AGENT_DEFAULT_MARKET", value)

        assert _get_settings().default_market is None

    @pytest.mark.ai
    def test_invalid_default_market_fails_at_startup(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify an unknown market code fails when loading settings.
        Why this matters: Bing ignores codes it does not know, so a typo would
            silently serve the wrong country. Failing at startup surfaces it
            during rollout instead of in front of users.
        Setup summary: Set an invalid default and expect settings to raise.
        """
        monkeypatch.setenv("BING_AGENT_DEFAULT_MARKET", "fr-XX")

        with pytest.raises(ValidationError):
            _get_settings()

    @pytest.mark.ai
    def test_blank_space_config_falls_back_to_the_deployment_default(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _patch_default_market(monkeypatch, "fr-FR")

        assert resolve_market(None) == "fr-FR"
        assert resolve_market("") == "fr-FR"

    @pytest.mark.ai
    def test_space_config_wins_over_the_deployment_default(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _patch_default_market(monkeypatch, "fr-FR")

        assert resolve_market("de-CH") == "de-CH"

    @pytest.mark.ai
    def test_no_market_anywhere_resolves_to_none(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify ``mkt`` is omitted when neither space nor deployment set it.
        Why this matters: Sending an empty or guessed market would change today's
            behaviour for every deployment that has not opted in.
        Setup summary: Clear the deployment default and resolve a blank value.
        """
        _patch_default_market(monkeypatch, None)

        assert resolve_market(None) is None

    @pytest.mark.ai
    def test_deployment_default_does_not_prefill_the_admin_form(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify the env default stays a runtime fallback.
        Why this matters: Baking it into the field default would show it as a
            configured choice and freeze it into every config saved afterwards,
            so changing the deployment default would stop reaching those spaces.
        Setup summary: Set a deployment default and inspect the config default.
        """
        _patch_default_market(monkeypatch, "fr-FR")

        assert BingAgentConfig().search_market is None
        assert (
            BingAgentConfig.model_json_schema()["properties"]["searchMarket"].get(
                "default"
            )
            is None
        )


class TestBingAgentRequestModel:
    @pytest.mark.ai
    def test_knobs_are_optional_request_fields(self) -> None:
        assert {"search_market", "search_freshness"} <= set(
            BingAgentSearchRequest.model_fields
        )
        assert "set_lang" not in BingAgentSearchRequest.model_fields
        request = BingAgentSearchRequest.model_validate({"query": "x"})
        assert request.search_market is None
        assert request.search_freshness is None

    @pytest.mark.ai
    def test_camel_case_aliases_accepted(self) -> None:
        request = BingAgentSearchRequest.model_validate(
            {"query": "x", "fetchSize": 7, "searchMarket": "fr-CH"},
        )
        assert request.fetch_size == 7
        assert request.search_market == "fr-CH"

    @pytest.mark.ai
    @pytest.mark.parametrize("freshness", ["Day", "Week", "Month"])
    def test_freshness_accepts_the_recency_presets(self, freshness: str) -> None:
        request = BingAgentSearchRequest.model_validate(
            {"query": "x", "searchFreshness": freshness},
        )
        assert request.search_freshness == freshness

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("searchMarket", "fr-XX"),
            ("searchMarket", "french"),
            ("searchMarket", "fr"),
            ("searchFreshness", "recently"),
            ("searchFreshness", "day"),
            ("searchFreshness", "last week"),
            # Absolute dates are Bing-valid but deliberately not offered: pinned
            # space-wide they freeze the space to a window that immediately rots.
            ("searchFreshness", "2026-02-04"),
            ("searchFreshness", "2026-01-01..2026-02-01"),
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
            would return results that look right while ignoring the request — and
            since these knobs are hashed into the agent name, each distinct string
            would also mint its own Foundry agent version.
        Setup summary: Validate a request per invalid value and expect a rejection.
        """
        with pytest.raises(ValidationError):
            BingAgentSearchRequest.model_validate({"query": "x", field: value})

    @pytest.mark.ai
    def test_output_schema_is_not_a_request_field(self) -> None:
        assert "output_schema" not in BingAgentSearchRequest.model_fields


class TestBingAgentMerge:
    @pytest.mark.ai
    def test_fixed_values_are_merged_into_the_request(self) -> None:
        config = BingAgentConfig(search_market="fr-CH", search_freshness="Week")

        request = config.merge({}, query="x")

        assert isinstance(request, BingAgentSearchRequest)
        assert request.search_market == "fr-CH"
        assert request.search_freshness == "Week"

    @pytest.mark.ai
    def test_blank_knobs_are_dropped(self) -> None:
        request = BingAgentConfig().merge({}, query="x")

        assert request.search_market is None
        assert request.search_freshness is None

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
