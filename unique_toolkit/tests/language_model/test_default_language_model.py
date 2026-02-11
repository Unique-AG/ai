import logging

import pytest

from unique_toolkit.language_model.default_language_model import (
    DEFAULT_GPT_4o,
    resolve_default_language_model,
)
from unique_toolkit.language_model.infos import LanguageModelName


class TestResolveDefaultLanguageModel:
    @pytest.mark.verified
    def test_resolve_default_language_model__returns_fallback__when_env_var_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Ensure fallback model is returned when no env configuration is present.
        Why this matters: Guarantees a stable default model selection in unconfigured environments.
        Setup summary: Clear test env var, resolve with explicit fallback, assert fallback is returned.
        """
        # Arrange
        monkeypatch.delenv("TEST_DEFAULT_LANGUAGE_MODEL", raising=False)

        # Act
        result = resolve_default_language_model(
            env_var="TEST_DEFAULT_LANGUAGE_MODEL",
            fallback=LanguageModelName.AZURE_GPT_4o_MINI_2024_0718,
        )

        # Assert
        assert result == LanguageModelName.AZURE_GPT_4o_MINI_2024_0718

    @pytest.mark.verified
    def test_resolve_default_language_model__returns_enum_value__when_env_matches_value(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify env values matching enum values resolve to the corresponding model.
        Why this matters: Supports direct configuration with serialized model values.
        Setup summary: Set env var to enum value string, resolve, and assert expected model.
        """
        # Arrange
        monkeypatch.setenv("TEST_DEFAULT_LANGUAGE_MODEL", DEFAULT_GPT_4o.value)

        # Act
        result = resolve_default_language_model(
            env_var="TEST_DEFAULT_LANGUAGE_MODEL",
            fallback=LanguageModelName.AZURE_GPT_4o_MINI_2024_0718,
        )

        # Assert
        assert result == DEFAULT_GPT_4o

    @pytest.mark.verified
    def test_resolve_default_language_model__returns_enum_member__when_env_matches_member_name(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify env values matching enum member names resolve correctly.
        Why this matters: Enables configuration by symbolic enum names across deployments.
        Setup summary: Set env var to enum member name, resolve, and assert selected model.
        """
        # Arrange
        monkeypatch.setenv("TEST_DEFAULT_LANGUAGE_MODEL", "AZURE_GPT_4o_2024_1120")

        # Act
        result = resolve_default_language_model(
            env_var="TEST_DEFAULT_LANGUAGE_MODEL",
            fallback=LanguageModelName.AZURE_GPT_4o_MINI_2024_0718,
        )

        # Assert
        assert result == LanguageModelName.AZURE_GPT_4o_2024_1120

    @pytest.mark.verified
    def test_resolve_default_language_model__returns_fallback__when_env_value_invalid(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Purpose: Ensure invalid env values trigger fallback model selection.
        Why this matters: Protects runtime behavior from misconfiguration and invalid model strings.
        Setup summary: Set invalid env value, capture warning logs, resolve, and assert fallback plus warning.
        """
        # Arrange
        monkeypatch.setenv("TEST_DEFAULT_LANGUAGE_MODEL", "NOT_A_REAL_MODEL")

        # Act
        with caplog.at_level(
            logging.WARNING,
            logger="unique_toolkit.language_model.default_language_model",
        ):
            result = resolve_default_language_model(
                env_var="TEST_DEFAULT_LANGUAGE_MODEL",
                fallback=LanguageModelName.AZURE_GPT_4o_MINI_2024_0718,
            )

        # Assert
        assert result == LanguageModelName.AZURE_GPT_4o_MINI_2024_0718
        assert "Invalid TEST_DEFAULT_LANGUAGE_MODEL='NOT_A_REAL_MODEL'" in caplog.text
