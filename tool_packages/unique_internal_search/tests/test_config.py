import pytest

from unique_internal_search.config import (
    ExperimentalFeatures,
    InternalSearchConfig,
    ToolResponseSystemReminderConfig,
)
from unique_internal_search.prompts import DEFAULT_TOOL_RESPONSE_SYSTEM_REMINDER_PROMPT


class TestSearchLanguageAliasChoices:
    """Tests for the search_language field alias resolution.

    The field accepts input via:
    - "ftsSearchLanguage" (legacy alias)
    - "searchLanguage" (camelCase alias)
    - "search_language" (python field name, via populate_by_name=True)
    """

    @pytest.mark.unit
    def test_search_language__uses_default__when_not_provided(self) -> None:
        config = InternalSearchConfig()
        assert config.search_language == "english"

    @pytest.mark.unit
    def test_search_language__accepts_fts_search_language_alias(self) -> None:
        config = InternalSearchConfig.model_validate({"ftsSearchLanguage": "german"})
        assert config.search_language == "german"

    @pytest.mark.unit
    def test_search_language__accepts_search_language_camel_alias(self) -> None:
        config = InternalSearchConfig.model_validate({"searchLanguage": "french"})
        assert config.search_language == "french"

    @pytest.mark.unit
    def test_search_language__accepts_python_field_name(self) -> None:
        config = InternalSearchConfig.model_validate({"search_language": "spanish"})
        assert config.search_language == "spanish"

    @pytest.mark.unit
    def test_search_language__canonical_key_takes_priority_over_legacy(self) -> None:
        config = InternalSearchConfig.model_validate(
            {"ftsSearchLanguage": "german", "searchLanguage": "french"}
        )
        assert config.search_language == "french"

    @pytest.mark.unit
    def test_search_language__canonical_key_takes_priority_over_legacy_inversely(
        self,
    ) -> None:
        config = InternalSearchConfig.model_validate(
            {"searchLanguage": "french", "ftsSearchLanguage": "german"}
        )
        assert config.search_language == "french"

    @pytest.mark.unit
    def test_search_language__serializes_with_camel_case_key(self) -> None:
        config = InternalSearchConfig.model_validate({"ftsSearchLanguage": "german"})
        dumped = config.model_dump(by_alias=True)
        assert "searchLanguage" in dumped
        assert dumped["searchLanguage"] == "german"
        assert "ftsSearchLanguage" not in dumped

    @pytest.mark.unit
    def test_search_language__serializes_with_python_field_name(self) -> None:
        config = InternalSearchConfig.model_validate({"ftsSearchLanguage": "german"})
        dumped = config.model_dump()
        assert "search_language" in dumped
        assert dumped["search_language"] == "german"

    @pytest.mark.unit
    def test_search_language__round_trips_through_camel_alias(self) -> None:
        original = InternalSearchConfig.model_validate({"searchLanguage": "italian"})
        dumped = original.model_dump(by_alias=True)
        restored = InternalSearchConfig.model_validate(dumped)
        assert restored.search_language == "italian"

    @pytest.mark.unit
    def test_search_language__round_trips_through_python_name(self) -> None:
        original = InternalSearchConfig.model_validate({"search_language": "italian"})
        dumped = original.model_dump()
        restored = InternalSearchConfig.model_validate(dumped)
        assert restored.search_language == "italian"

    @pytest.mark.unit
    def test_search_language__round_trips_from_legacy_fts_alias(self) -> None:
        original = InternalSearchConfig.model_validate(
            {"ftsSearchLanguage": "japanese"}
        )
        dumped = original.model_dump(by_alias=True)
        restored = InternalSearchConfig.model_validate(dumped)
        assert restored.search_language == "japanese"


class TestToolResponseSystemReminderConfig:
    """Tests for ToolResponseSystemReminderConfig and its integration in ExperimentalFeatures."""

    @pytest.mark.unit
    def test_defaults__disabled_with_default_prompt(self) -> None:
        cfg = ToolResponseSystemReminderConfig()
        assert cfg.enabled is False
        assert cfg.system_reminder_prompt == DEFAULT_TOOL_RESPONSE_SYSTEM_REMINDER_PROMPT

    @pytest.mark.unit
    def test_get_reminder_prompt__returns_empty__when_disabled(self) -> None:
        cfg = ToolResponseSystemReminderConfig(enabled=False)
        assert cfg.get_reminder_prompt == ""

    @pytest.mark.unit
    def test_get_reminder_prompt__returns_prompt__when_enabled(self) -> None:
        cfg = ToolResponseSystemReminderConfig(enabled=True)
        assert cfg.get_reminder_prompt == DEFAULT_TOOL_RESPONSE_SYSTEM_REMINDER_PROMPT

    @pytest.mark.unit
    def test_get_reminder_prompt__returns_custom_prompt__when_enabled(self) -> None:
        custom = "Always cite your sources."
        cfg = ToolResponseSystemReminderConfig(enabled=True, system_reminder_prompt=custom)
        assert cfg.get_reminder_prompt == custom

    @pytest.mark.unit
    def test_get_reminder_prompt__returns_empty__when_disabled_with_custom_prompt(self) -> None:
        custom = "Always cite your sources."
        cfg = ToolResponseSystemReminderConfig(enabled=False, system_reminder_prompt=custom)
        assert cfg.get_reminder_prompt == ""

    @pytest.mark.unit
    def test_experimental_features__contains_default_reminder_config(self) -> None:
        features = ExperimentalFeatures()
        assert isinstance(features.tool_response_system_reminder, ToolResponseSystemReminderConfig)
        assert features.tool_response_system_reminder.enabled is False

    @pytest.mark.unit
    def test_internal_search_config__experimental_features_default(self) -> None:
        config = InternalSearchConfig()
        reminder = config.experimental_features.tool_response_system_reminder
        assert isinstance(reminder, ToolResponseSystemReminderConfig)
        assert reminder.enabled is False
        assert reminder.get_reminder_prompt == ""

    @pytest.mark.unit
    def test_internal_search_config__round_trips_reminder_enabled(self) -> None:
        config = InternalSearchConfig.model_validate(
            {
                "experimentalFeatures": {
                    "toolResponseSystemReminder": {
                        "enabled": True,
                        "systemReminderPrompt": "Cite everything!",
                    }
                }
            }
        )
        reminder = config.experimental_features.tool_response_system_reminder
        assert reminder.enabled is True
        assert reminder.get_reminder_prompt == "Cite everything!"
