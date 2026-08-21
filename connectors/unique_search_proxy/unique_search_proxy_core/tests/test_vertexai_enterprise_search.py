"""Tests for Vertex AI enterprise-search enforcement (UN-24347)."""

from __future__ import annotations

import pytest
from unique_toolkit._common.pydantic.rjsf_tags import ui_schema_for_model

from unique_search_proxy_core.agent_engines.vertexai.schema import (
    VertexAIAgentConfig,
    _enterprise_search_rjsf_tag,
    _get_force_activate_enterprise_search_description,
)
from unique_search_proxy_core.agent_engines.vertexai.settings import (
    _get_settings,
    resolve_enable_enterprise_search,
    vertex_ai_env_settings,
)


@pytest.fixture
def unlock_enterprise_search(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        vertex_ai_env_settings,
        "force_activate_enterprise_search",
        False,
    )


@pytest.fixture
def lock_enterprise_search(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        vertex_ai_env_settings,
        "force_activate_enterprise_search",
        True,
    )


class TestVertexAIEnvSettings:
    @pytest.mark.ai
    @pytest.mark.unit
    def test_force_activate_reads_env_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: Provisioning env var turns on the ZDR enterprise-search lock.
        Why this matters: Infra must be able to pin the flag per tenant without code changes.
        Setup summary: Set VERTEXAI_AGENT_FORCE_ACTIVATE_ENTERPRISE_SEARCH=true and reload settings.
        """
        monkeypatch.setenv("VERTEXAI_AGENT_FORCE_ACTIVATE_ENTERPRISE_SEARCH", "true")
        settings = _get_settings()
        assert settings.force_activate_enterprise_search is True

    @pytest.mark.ai
    @pytest.mark.unit
    def test_force_activate_defaults_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: Non-ZDR tenants keep enterprise search optional.
        Why this matters: Forcing the enterprise edition on every tenant would raise cost.
        Setup summary: Clear the env var and reload settings.
        """
        monkeypatch.delenv(
            "VERTEXAI_AGENT_FORCE_ACTIVATE_ENTERPRISE_SEARCH", raising=False
        )
        settings = _get_settings()
        assert settings.force_activate_enterprise_search is False


class TestResolveEnableEnterpriseSearch:
    @pytest.mark.ai
    @pytest.mark.unit
    @pytest.mark.usefixtures("unlock_enterprise_search")
    def test_passthrough_when_unlocked(self) -> None:
        """
        Purpose: Requested false stays false when infra is not locking the toggle.
        Why this matters: Non-ZDR clients must still choose the cheaper standard edition.
        Setup summary: Unlock the flag and resolve a false request.
        """
        assert resolve_enable_enterprise_search(False) is False
        assert resolve_enable_enterprise_search(True) is True

    @pytest.mark.ai
    @pytest.mark.unit
    @pytest.mark.usefixtures("lock_enterprise_search")
    def test_forces_true_when_locked(self) -> None:
        """
        Purpose: A false request is coerced to true when the ZDR lock is on.
        Why this matters: Unchecking the toggle must not drop a ZDR tenant off enterprise search.
        Setup summary: Lock the flag and resolve a false request.
        """
        assert resolve_enable_enterprise_search(False) is True
        assert resolve_enable_enterprise_search(None) is True


class TestVertexAIAgentConfigEnterpriseSearch:
    @pytest.mark.ai
    @pytest.mark.unit
    @pytest.mark.usefixtures("unlock_enterprise_search")
    def test_explicit_false_allowed_when_unlocked(self) -> None:
        """
        Purpose: Config can disable enterprise search for non-ZDR tenants.
        Why this matters: The UI toggle must remain a real choice when infra is not enforcing it.
        Setup summary: Unlock the flag and construct config with enable_enterprise_search=False.
        """
        config = VertexAIAgentConfig(enable_enterprise_search=False)
        assert config.enable_enterprise_search is False

    @pytest.mark.ai
    @pytest.mark.unit
    @pytest.mark.usefixtures("lock_enterprise_search")
    def test_explicit_false_overridden_when_locked(self) -> None:
        """
        Purpose: Saved config cannot turn enterprise search off for ZDR tenants.
        Why this matters: Accidental uncheck would silently lose the ZDR / regional processing guarantee.
        Setup summary: Lock the flag and construct config with enable_enterprise_search=False.
        """
        config = VertexAIAgentConfig(enable_enterprise_search=False)
        assert config.enable_enterprise_search is True

    @pytest.mark.ai
    @pytest.mark.unit
    @pytest.mark.usefixtures("lock_enterprise_search")
    def test_default_is_true_when_locked(self) -> None:
        """
        Purpose: Omitted field defaults to on when infra is locking enterprise search.
        Why this matters: New spaces on ZDR tenants must start on the enterprise edition.
        Setup summary: Lock the flag and construct config with no explicit value.
        """
        config = VertexAIAgentConfig()
        assert config.enable_enterprise_search is True


class TestEnterpriseSearchRjsf:
    @pytest.mark.ai
    @pytest.mark.unit
    @pytest.mark.usefixtures("unlock_enterprise_search")
    def test_help_and_disabled_when_unlocked(self) -> None:
        """
        Purpose: The checkbox stays editable with the SEC4 help text for non-ZDR tenants.
        Why this matters: Operators need to understand the toggle and still be able to leave it off.
        Setup summary: Unlock the flag and inspect the RJSF tag plus generated UI schema.
        """
        tag = _enterprise_search_rjsf_tag()
        assert tag.attrs["ui:disabled"] is False
        assert "SEC4-compliant" in _get_force_activate_enterprise_search_description()

        ui = ui_schema_for_model(VertexAIAgentConfig)
        field_ui = ui.get("enableEnterpriseSearch") or ui.get(
            "enable_enterprise_search"
        )
        assert field_ui is not None
        assert field_ui["ui:widget"] == "checkbox"

    @pytest.mark.ai
    @pytest.mark.unit
    @pytest.mark.usefixtures("lock_enterprise_search")
    def test_help_and_disabled_when_locked(self) -> None:
        """
        Purpose: The checkbox is disabled and help explains infra enforcement when locked.
        Why this matters: ZDR clients must not be able to uncheck the toggle in the config form.
        Setup summary: Lock the flag and inspect the dynamically built RJSF tag.
        """
        tag = _enterprise_search_rjsf_tag()
        assert tag.attrs["ui:disabled"] is True
        assert (
            _get_force_activate_enterprise_search_description()
            == "This parameter has been enforced by infra team."
        )
