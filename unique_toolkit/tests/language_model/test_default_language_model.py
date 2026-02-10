import logging

import pytest

from unique_toolkit.language_model.default_language_model import (
    DEFAULT_GPT_4o,
    resolve_default_language_model,
)
from unique_toolkit.language_model.infos import LanguageModelName

@pytest.mark.verified
class TestResolveDefaultLanguageModel:
    def test_returns_fallback_when_env_var_missing(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("TEST_DEFAULT_LANGUAGE_MODEL", raising=False)

        result = resolve_default_language_model(
            env_var="TEST_DEFAULT_LANGUAGE_MODEL",
            fallback=LanguageModelName.AZURE_GPT_4o_MINI_2024_0718,
        )

        assert result == LanguageModelName.AZURE_GPT_4o_MINI_2024_0718

    def test_resolves_from_enum_value(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TEST_DEFAULT_LANGUAGE_MODEL", DEFAULT_GPT_4o)

        result = resolve_default_language_model(
            env_var="TEST_DEFAULT_LANGUAGE_MODEL",
            fallback=LanguageModelName.AZURE_GPT_4o_MINI_2024_0718,
        )

        assert result == DEFAULT_GPT_4o

    def test_resolves_from_enum_member_name(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TEST_DEFAULT_LANGUAGE_MODEL", "AZURE_GPT_4o_2024_1120")

        result = resolve_default_language_model(
            env_var="TEST_DEFAULT_LANGUAGE_MODEL",
            fallback=LanguageModelName.AZURE_GPT_4o_MINI_2024_0718,
        )

        assert result == LanguageModelName.AZURE_GPT_4o_2024_1120

    def test_invalid_env_value_logs_warning_and_uses_fallback(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ):
        monkeypatch.setenv("TEST_DEFAULT_LANGUAGE_MODEL", "NOT_A_REAL_MODEL")

        with caplog.at_level(
            logging.WARNING,
            logger="unique_toolkit.language_model.default_language_model",
        ):
            result = resolve_default_language_model(
                env_var="TEST_DEFAULT_LANGUAGE_MODEL",
                fallback=LanguageModelName.AZURE_GPT_4o_MINI_2024_0718,
            )

        assert result == LanguageModelName.AZURE_GPT_4o_MINI_2024_0718
        assert "Invalid TEST_DEFAULT_LANGUAGE_MODEL='NOT_A_REAL_MODEL'" in caplog.text
