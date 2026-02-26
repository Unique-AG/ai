import pytest

from unique_internal_search.config import InternalSearchConfig


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
