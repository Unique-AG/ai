"""Tests for ``unique_orchestrator.settings``.

These tests exercise:

* Default values on the ``Base`` schema (the warning text and the loop /
  tool-call ceilings the orchestrator relies on at runtime).
* Environment-variable loading via the ``UNIQUE_ORCHESTRATOR_`` prefix
  configured by ``get_model_config``.
* The ``get_model_config`` factory's branching between the dev ``.env``
  file and the ``tests/test.env`` file.
* The ``get_settings`` switch that returns a ``TestSettings`` instance
  when ``pytest`` is loaded and a ``Settings`` instance otherwise.
* The module-level ``env_settings`` singleton, which is the entry point
  every other module in the package uses.

Lives under the top-level ``tests/`` directory so the CI coverage runner
(``check-coverage.sh``) picks it up — collection in CI starts at
``tests/`` and does not descend into ``unique_orchestrator/tests/``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from unique_orchestrator.settings import (
    EMPTY_MESSAGE_WARNING,
    Base,
    Settings,
    env_settings,
    get_model_config,
    get_settings,
)
from unique_orchestrator.settings import (
    TestSettings as PytestVariantSettings,
)


def _clear_orchestrator_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove every ``UNIQUE_ORCHESTRATOR_*`` env var from the process.

    Settings classes pick up env vars from ``os.environ`` at instantiation
    time, so anything left over from another test (or from the shell that
    launched pytest) would silently override the defaults we're asserting
    on. This keeps each test deterministic.
    """
    for key in list(os.environ):
        if key.upper().startswith("UNIQUE_ORCHESTRATOR_"):
            monkeypatch.delenv(key, raising=False)


class TestBaseDefaults:
    @pytest.mark.ai
    def test_base__uses_empty_message_warning_constant__by_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: The default ``empty_message_warning`` matches the module-level
            ``EMPTY_MESSAGE_WARNING`` constant.
        Why this matters: This text is rendered to end users whenever the LLM
            produces no output; an accidental drift between the constant and
            the field default would silently change user-facing copy.
        Setup summary: Clear all UNIQUE_ORCHESTRATOR_* env vars, instantiate
            Base, compare against the constant.
        """
        _clear_orchestrator_env(monkeypatch)

        settings = Base()

        assert settings.empty_message_warning == EMPTY_MESSAGE_WARNING

    @pytest.mark.ai
    def test_base__uses_default_loop_iteration_limit__when_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: The default ``limit_max_loop_iterations`` is 100.
        Why this matters: This bound caps runaway agent loops; lowering it
            silently would degrade quality, raising it silently would risk
            unbounded cost. Pin the contract.
        Setup summary: Clear env vars, instantiate Base, assert default.
        """
        _clear_orchestrator_env(monkeypatch)

        settings = Base()

        assert settings.limit_max_loop_iterations == 100

    @pytest.mark.ai
    def test_base__uses_default_tool_call_limit__when_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: The default ``limit_max_tool_calls_per_iteration`` is 50.
        Why this matters: Same rationale as the loop cap — pin the contract
            so accidental edits to the default are caught here.
        Setup summary: Clear env vars, instantiate Base, assert default.
        """
        _clear_orchestrator_env(monkeypatch)

        settings = Base()

        assert settings.limit_max_tool_calls_per_iteration == 50

    @pytest.mark.ai
    def test_empty_message_warning_constant__is_non_empty_user_facing_text(
        self,
    ) -> None:
        """
        Purpose: The module-level ``EMPTY_MESSAGE_WARNING`` is a non-empty
            string mentioning the language model.
        Why this matters: Empty or placeholder copy would surface to users in
            the worst possible moment (LLM produced nothing). A trivial guard
            against a copy regression.
        Setup summary: Inspect the imported constant directly.
        """
        assert isinstance(EMPTY_MESSAGE_WARNING, str)
        assert EMPTY_MESSAGE_WARNING.strip() != ""
        assert "language model" in EMPTY_MESSAGE_WARNING.lower()


class TestSettingsEnvLoading:
    """Verify the ``UNIQUE_ORCHESTRATOR_`` env prefix actually wires through."""

    @pytest.mark.ai
    def test_settings__loads_int_limits__from_prefixed_env_vars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: ``Settings`` reads ``UNIQUE_ORCHESTRATOR_*`` env vars and
            coerces them to the declared types.
        Why this matters: Operators tune these limits exclusively via env
            vars. A regression in the prefix or coercion would silently
            keep the defaults in production.
        Setup summary: Set prefixed env vars, instantiate Settings, assert
            values are loaded and typed.
        """
        _clear_orchestrator_env(monkeypatch)
        monkeypatch.setenv("UNIQUE_ORCHESTRATOR_LIMIT_MAX_LOOP_ITERATIONS", "7")
        monkeypatch.setenv(
            "UNIQUE_ORCHESTRATOR_LIMIT_MAX_TOOL_CALLS_PER_ITERATION", "11"
        )

        settings = Settings()

        assert settings.limit_max_loop_iterations == 7
        assert settings.limit_max_tool_calls_per_iteration == 11

    @pytest.mark.ai
    def test_settings__is_case_insensitive__for_env_var_names(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: Lower-cased prefixed env vars are still picked up.
        Why this matters: ``case_sensitive=False`` is part of the documented
            contract in ``get_model_config``. Removing it would break
            deployments that set lowercase env vars (common in .env files).
        Setup summary: Set the lowercase form, instantiate Settings, assert.
        """
        _clear_orchestrator_env(monkeypatch)
        monkeypatch.setenv("unique_orchestrator_limit_max_loop_iterations", "3")

        settings = Settings()

        assert settings.limit_max_loop_iterations == 3

    @pytest.mark.ai
    def test_settings__ignores_extra_env_vars__not_declared_on_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: Setting an unrelated ``UNIQUE_ORCHESTRATOR_FOO`` does not
            raise.
        Why this matters: ``extra="ignore"`` shields the orchestrator from
            crashing when unrelated env vars share the namespace (e.g.,
            future feature flags rolled out before code lands).
        Setup summary: Set an undeclared prefixed env var, instantiate
            Settings, ensure no exception and defaults remain.
        """
        _clear_orchestrator_env(monkeypatch)
        monkeypatch.setenv("UNIQUE_ORCHESTRATOR_FOO_BAR_BAZ", "anything")

        settings = Settings()

        assert settings.limit_max_loop_iterations == 100

    @pytest.mark.ai
    def test_settings__does_not_read__unprefixed_env_vars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: An env var matching a field name but missing the prefix is
            not picked up by ``Settings``.
        Why this matters: Without the prefix gate, generic env vars like
            ``LIMIT_MAX_LOOP_ITERATIONS`` could collide with values from
            other tools running in the same process.
        Setup summary: Set the unprefixed form, instantiate Settings, assert
            the default still applies.
        """
        _clear_orchestrator_env(monkeypatch)
        monkeypatch.setenv("LIMIT_MAX_LOOP_ITERATIONS", "999")

        settings = Settings()

        assert settings.limit_max_loop_iterations == 100

    @pytest.mark.ai
    def test_pytest_variant_settings__inherits_base_fields_and_prefix(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: The pytest variant (``settings.TestSettings``) reads the
            same env prefix and exposes the same fields as ``Settings``.
        Why this matters: Tests rely on this variant to deliver identical
            shape with a different env file. Drift here would cause tests
            and production code to diverge invisibly.
        Setup summary: Set a prefixed env var, instantiate the variant,
            assert the value is present.
        """
        _clear_orchestrator_env(monkeypatch)
        monkeypatch.setenv("UNIQUE_ORCHESTRATOR_LIMIT_MAX_LOOP_ITERATIONS", "42")

        settings = PytestVariantSettings()

        assert isinstance(settings, Base)
        assert settings.limit_max_loop_iterations == 42


class TestGetModelConfig:
    @pytest.mark.ai
    def test_get_model_config__returns_orchestrator_prefix_and_ignore_extras(
        self,
    ) -> None:
        """
        Purpose: The factory always sets the documented prefix, encoding,
            ``extra=ignore`` and case-insensitive matching.
        Why this matters: Every consumer in the codebase relies on these
            invariants; encoding them as an explicit assertion guards
            against accidental edits to the dict literal.
        Setup summary: Call the factory, inspect the returned dict.
        """
        config = get_model_config()

        assert config.get("env_prefix") == "UNIQUE_ORCHESTRATOR_"
        assert config.get("extra") == "ignore"
        assert config.get("case_sensitive") is False
        assert config.get("env_file_encoding") == "utf-8"

    @pytest.mark.ai
    def test_get_model_config__defaults_to_dev_env_file__at_cwd_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: With no argument (``env="dev"``), the env_file resolves to
            ``<cwd>/.env``.
        Why this matters: Local development assumes a project-root ``.env``;
            switching the resolution rule would silently stop loading
            developer credentials.
        Setup summary: chdir into a tmp directory, call the factory, assert
            the env_file path.
        """
        monkeypatch.chdir(tmp_path)

        config = get_model_config()

        assert config.get("env_file") == tmp_path / ".env"

    @pytest.mark.ai
    def test_get_model_config__test_env__uses_tests_test_dot_env_at_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: With ``env="test"``, the env_file resolves to
            ``<cwd>/tests/test.env``.
        Why this matters: The pytest path must be deterministic and cwd-
            relative for CI runs and per-package test suites.
        Setup summary: chdir into a tmp directory, call the factory with
            ``env="test"``, assert the env_file path.
        """
        monkeypatch.chdir(tmp_path)

        config = get_model_config(env="test")

        assert config.get("env_file") == tmp_path / "tests" / "test.env"

    @pytest.mark.ai
    def test_get_model_config__dev_env__uses_dot_env_at_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: ``env="dev"`` explicitly resolves to ``<cwd>/.env``.
        Why this matters: Pins the documented behavior of the explicit
            ``"dev"`` argument (mirroring the implicit default).
        Setup summary: chdir into a tmp directory, call the factory with
            ``env="dev"``, assert the env_file path.
        """
        monkeypatch.chdir(tmp_path)

        config = get_model_config(env="dev")

        assert config.get("env_file") == tmp_path / ".env"


class TestGetSettings:
    @pytest.mark.ai
    def test_get_settings__returns_pytest_variant__when_under_pytest(self) -> None:
        """
        Purpose: When ``pytest`` is in ``sys.modules`` (always true in this
            test run), ``get_settings`` returns the pytest variant (an
            instance of ``settings.TestSettings``).
        Why this matters: Tests across the codebase assume the test variant
            is auto-selected without per-call wiring.
        Setup summary: Call ``get_settings`` directly and check the type.
        """
        assert "pytest" in sys.modules

        result = get_settings()

        assert type(result) is PytestVariantSettings

    @pytest.mark.ai
    def test_get_settings__returns_settings__when_pytest_not_loaded(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: With ``"pytest"`` removed from ``sys.modules``,
            ``get_settings`` returns the production ``Settings`` instance.
        Why this matters: This is the production code path; without coverage
            of the non-pytest branch, refactoring ``get_settings`` could
            ship a dev-only configuration to production unnoticed.
        Setup summary: Replace ``sys.modules`` with a copy that excludes the
            ``pytest`` key, call ``get_settings``, assert the type.
        """
        modules_without_pytest = {k: v for k, v in sys.modules.items() if k != "pytest"}
        monkeypatch.setattr(sys, "modules", modules_without_pytest)

        assert "pytest" not in sys.modules

        result = get_settings()

        assert type(result) is Settings


class TestEnvSettingsSingleton:
    @pytest.mark.ai
    def test_env_settings__is_a_base_instance(self) -> None:
        """
        Purpose: The module-level ``env_settings`` is an instance of
            ``Base``.
        Why this matters: Other modules import ``env_settings`` and rely on
            its declared attributes; a regression that left the singleton
            unset (or replaced with the class) would surface only at first
            use, far from the cause.
        Setup summary: Inspect the imported singleton directly.
        """
        assert isinstance(env_settings, Base)

    @pytest.mark.ai
    def test_env_settings__exposes_documented_fields(self) -> None:
        """
        Purpose: The singleton exposes ``empty_message_warning``,
            ``limit_max_loop_iterations``, and
            ``limit_max_tool_calls_per_iteration``.
        Why this matters: These three attributes form the public contract
            consumed across the orchestrator. Renaming or dropping any of
            them must trip a test rather than a runtime AttributeError.
        Setup summary: Read each attribute on the singleton.
        """
        assert isinstance(env_settings.empty_message_warning, str)
        assert isinstance(env_settings.limit_max_loop_iterations, int)
        assert isinstance(env_settings.limit_max_tool_calls_per_iteration, int)
