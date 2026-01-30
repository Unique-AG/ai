"""Tests for hallucination constants and configuration."""

import re

import pytest

from unique_toolkit.agentic.evaluation.hallucination.constants import (
    HallucinationConfig,
    HallucinationPromptsConfig,
    SourceSelectionMode,
    hallucination_metric_default_config,
    hallucination_required_input_fields,
)
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationMetricInputFieldName,
    EvaluationMetricName,
)


@pytest.mark.ai
def test_source_selection_mode__has_from_ids_mode__as_enum_value() -> None:
    """
    Purpose: Verify that FROM_IDS mode exists in SourceSelectionMode enum.
    Why this matters: FROM_IDS is a core selection mode for chunk identification.
    Setup summary: Check enum attribute exists and has correct value.
    """
    # Arrange - No setup needed

    # Act & Assert
    assert hasattr(SourceSelectionMode, "FROM_IDS")
    assert SourceSelectionMode.FROM_IDS == "FROM_IDS"


@pytest.mark.ai
def test_source_selection_mode__has_from_order_mode__as_enum_value() -> None:
    """
    Purpose: Verify that FROM_ORDER mode exists in SourceSelectionMode enum.
    Why this matters: FROM_ORDER enables index-based chunk selection.
    Setup summary: Check enum attribute exists and has correct value.
    """
    # Arrange - No setup needed

    # Act & Assert
    assert hasattr(SourceSelectionMode, "FROM_ORDER")
    assert SourceSelectionMode.FROM_ORDER == "FROM_ORDER"


@pytest.mark.ai
def test_source_selection_mode__has_from_original_response_mode__as_enum_value() -> (
    None
):
    """
    Purpose: Verify that FROM_ORIGINAL_RESPONSE mode exists in SourceSelectionMode enum.
    Why this matters: FROM_ORIGINAL_RESPONSE enables text-based reference extraction.
    Setup summary: Check enum attribute exists and has correct value.
    """
    # Arrange - No setup needed

    # Act & Assert
    assert hasattr(SourceSelectionMode, "FROM_ORIGINAL_RESPONSE")
    assert SourceSelectionMode.FROM_ORIGINAL_RESPONSE == "FROM_ORIGINAL_RESPONSE"


@pytest.mark.ai
def test_source_selection_mode__uses_strings__for_all_mode_values() -> None:
    """
    Purpose: Verify that all SourceSelectionMode enum values are strings.
    Why this matters: String values enable easy serialization and comparison.
    Setup summary: Iterate all modes, assert each value is string type.
    """
    # Arrange - No setup needed

    # Act & Assert
    for mode in SourceSelectionMode:
        assert isinstance(mode.value, str)


@pytest.mark.ai
def test_source_selection_mode__uses_uppercase__for_all_mode_values() -> None:
    """
    Purpose: Verify that all SourceSelectionMode values are uppercase.
    Why this matters: Consistent naming convention for enum values.
    Setup summary: Iterate all modes, assert each value is uppercase.
    """
    # Arrange - No setup needed

    # Act & Assert
    for mode in SourceSelectionMode:
        assert mode.value.isupper()


@pytest.mark.ai
def test_hallucination_prompts_config__loads_templates_from_files__on_default_initialization() -> (
    None
):
    """
    Purpose: Verify that default initialization loads template files automatically.
    Why this matters: Templates must be loaded for hallucination evaluation to work.
    Setup summary: Create config with defaults, assert templates are non-empty.
    """
    # Arrange - No setup needed

    # Act
    config: HallucinationPromptsConfig = HallucinationPromptsConfig()

    # Assert
    assert len(config.system_prompt_template) > 0
    assert len(config.user_prompt_template) > 0


@pytest.mark.ai
def test_hallucination_prompts_config__contains_jinja_syntax__in_loaded_templates() -> (
    None
):
    """
    Purpose: Verify that loaded templates contain Jinja2 template syntax.
    Why this matters: Templates must support dynamic content rendering.
    Setup summary: Load default config, assert Jinja2 syntax present.
    """
    # Arrange - No setup needed

    # Act
    config: HallucinationPromptsConfig = HallucinationPromptsConfig()

    # Assert
    assert "{%" in config.system_prompt_template
    assert "{{" in config.user_prompt_template


@pytest.mark.ai
def test_hallucination_prompts_config__accepts_custom_templates__on_initialization() -> (
    None
):
    """
    Purpose: Verify that templates can be overridden during initialization.
    Why this matters: Allows customization of hallucination detection prompts.
    Setup summary: Initialize with custom prompts, assert they override defaults.
    """
    # Arrange
    custom_system: str = "Custom system prompt"
    custom_user: str = "Custom user prompt"

    # Act
    config: HallucinationPromptsConfig = HallucinationPromptsConfig(
        system_prompt_template=custom_system,
        user_prompt_template=custom_user,
    )

    # Assert
    assert config.system_prompt_template == custom_system
    assert config.user_prompt_template == custom_user


@pytest.mark.ai
def test_hallucination_prompts_config__allows_modification__after_initialization() -> (
    None
):
    """
    Purpose: Verify that templates can be modified after config creation.
    Why this matters: Enables runtime template customization.
    Setup summary: Create config, modify templates, assert new values.
    """
    # Arrange
    config: HallucinationPromptsConfig = HallucinationPromptsConfig()

    # Act
    config.system_prompt_template = "New system"
    config.user_prompt_template = "New user"

    # Assert
    assert config.system_prompt_template == "New system"
    assert config.user_prompt_template == "New user"


@pytest.mark.ai
def test_hallucination_config__defaults_to_from_original_response__for_source_selection() -> (
    None
):
    """
    Purpose: Verify that default source selection mode is FROM_ORIGINAL_RESPONSE.
    Why this matters: This is the most accurate mode for extracting used sources.
    Setup summary: Create default config, assert source selection mode.
    """
    # Arrange - No setup needed

    # Act
    config: HallucinationConfig = HallucinationConfig()

    # Assert
    assert config.source_selection_mode == SourceSelectionMode.FROM_ORIGINAL_RESPONSE


@pytest.mark.ai
def test_hallucination_config__has_default_regex_pattern__for_source_references() -> (
    None
):
    """
    Purpose: Verify that default reference_pattern is correctly configured.
    Why this matters: Pattern must match common source reference formats.
    Setup summary: Create default config, assert reference_pattern value.
    """
    # Arrange - No setup needed

    # Act
    config: HallucinationConfig = HallucinationConfig()

    # Assert
    assert config.reference_pattern == r"[\[<]?source(\d+)[>\]]?"


@pytest.mark.ai
def test_hallucination_config__uses_valid_regex__for_reference_pattern() -> None:
    """
    Purpose: Verify that reference_pattern is a valid regular expression.
    Why this matters: Invalid regex would cause runtime errors during extraction.
    Setup summary: Create config, compile reference_pattern, assert no errors.
    """
    # Arrange
    config: HallucinationConfig = HallucinationConfig()

    # Act & Assert
    try:
        re.compile(config.reference_pattern)
    except re.error:
        pytest.fail("reference_pattern is not a valid regex")


@pytest.mark.ai
def test_hallucination_config__is_disabled_by_default__for_safety() -> None:
    """
    Purpose: Verify that hallucination metric is disabled by default.
    Why this matters: Prevents unexpected evaluation costs and behavior.
    Setup summary: Create default config, assert enabled is False.
    """
    # Arrange - No setup needed

    # Act
    config: HallucinationConfig = HallucinationConfig()

    # Assert
    assert config.enabled is False


@pytest.mark.ai
def test_hallucination_config__has_hallucination_metric_name__by_default() -> None:
    """
    Purpose: Verify that metric name is HALLUCINATION.
    Why this matters: Correct metric identification for evaluation system.
    Setup summary: Create default config, assert name field.
    """
    # Arrange - No setup needed

    # Act
    config: HallucinationConfig = HallucinationConfig()

    # Assert
    assert config.name == EvaluationMetricName.HALLUCINATION


@pytest.mark.ai
def test_hallucination_config__includes_prompts_config__on_initialization() -> None:
    """
    Purpose: Verify that config has prompts_config field with loaded templates.
    Why this matters: Prompts are required for hallucination evaluation.
    Setup summary: Create config, assert prompts_config exists and is correct type.
    """
    # Arrange - No setup needed

    # Act
    config: HallucinationConfig = HallucinationConfig()

    # Assert
    assert hasattr(config, "prompts_config")
    assert isinstance(config.prompts_config, HallucinationPromptsConfig)


@pytest.mark.ai
def test_hallucination_config__loads_templates_in_prompts_config__by_default() -> None:
    """
    Purpose: Verify that prompts_config is initialized with loaded templates.
    Why this matters: Templates must be available for evaluation without extra setup.
    Setup summary: Create config, assert prompts_config templates are non-empty.
    """
    # Arrange - No setup needed

    # Act
    config: HallucinationConfig = HallucinationConfig()

    # Assert
    assert len(config.prompts_config.system_prompt_template) > 0
    assert len(config.prompts_config.user_prompt_template) > 0


@pytest.mark.ai
def test_hallucination_config__has_score_mapping_dictionaries__for_labels_and_titles() -> (
    None
):
    """
    Purpose: Verify that config has score_to_label and score_to_title mappings.
    Why this matters: Score mappings enable UI display of evaluation results.
    Setup summary: Create config, assert mapping attributes exist.
    """
    # Arrange - No setup needed

    # Act
    config: HallucinationConfig = HallucinationConfig()

    # Assert
    assert hasattr(config, "score_to_label")
    assert hasattr(config, "score_to_title")


@pytest.mark.ai
def test_hallucination_config__maps_scores_to_color_labels__correctly() -> None:
    """
    Purpose: Verify that score_to_label has expected color mappings.
    Why this matters: Color coding provides intuitive hallucination severity indication.
    Setup summary: Create config, assert score to color mappings.
    """
    # Arrange - No setup needed

    # Act
    config: HallucinationConfig = HallucinationConfig()

    # Assert
    assert config.score_to_label["LOW"] == "GREEN"
    assert config.score_to_label["MEDIUM"] == "YELLOW"
    assert config.score_to_label["HIGH"] == "RED"


@pytest.mark.ai
def test_hallucination_config__includes_hallucination_in_titles__for_all_scores() -> (
    None
):
    """
    Purpose: Verify that score_to_title contains "Hallucination" in all titles.
    Why this matters: Titles should clearly identify the metric being evaluated.
    Setup summary: Create config, assert "Hallucination" present in all titles.
    """
    # Arrange - No setup needed

    # Act
    config: HallucinationConfig = HallucinationConfig()

    # Assert
    assert "Hallucination" in config.score_to_title["LOW"]
    assert "Hallucination" in config.score_to_title["MEDIUM"]
    assert "Hallucination" in config.score_to_title["HIGH"]


@pytest.mark.ai
def test_hallucination_config__accepts_custom_source_selection_mode__on_initialization() -> (
    None
):
    """
    Purpose: Verify that source_selection_mode can be customized.
    Why this matters: Different use cases may require different selection strategies.
    Setup summary: Initialize with custom mode, assert it's set correctly.
    """
    # Arrange
    custom_mode: SourceSelectionMode = SourceSelectionMode.FROM_IDS

    # Act
    config: HallucinationConfig = HallucinationConfig(source_selection_mode=custom_mode)

    # Assert
    assert config.source_selection_mode == SourceSelectionMode.FROM_IDS


@pytest.mark.ai
def test_hallucination_config__accepts_custom_reference_pattern__on_initialization() -> None:
    """
    Purpose: Verify that reference_pattern can be customized during initialization.
    Why this matters: Allows support for different reference citation formats.
    Setup summary: Initialize with custom pattern, assert it's stored.
    """
    # Arrange
    custom_pattern: str = r"ref:(\d+)"

    # Act
    config: HallucinationConfig = HallucinationConfig(reference_pattern=custom_pattern)

    # Assert
    assert config.reference_pattern == custom_pattern


@pytest.mark.ai
def test_hallucination_config__can_be_enabled__via_initialization() -> None:
    """
    Purpose: Verify that metric can be enabled during config creation.
    Why this matters: Allows explicit opt-in to hallucination evaluation.
    Setup summary: Initialize with enabled=True, assert enabled state.
    """
    # Arrange - No setup needed

    # Act
    config: HallucinationConfig = HallucinationConfig(enabled=True)

    # Assert
    assert config.enabled is True


@pytest.mark.ai
def test_hallucination_config__serializes_to_dict__with_all_fields() -> None:
    """
    Purpose: Verify that config can be serialized to dictionary format.
    Why this matters: Required for persistence and API serialization.
    Setup summary: Create config with custom values, serialize, assert structure.
    """
    # Arrange - No setup needed

    # Act
    config: HallucinationConfig = HallucinationConfig(
        enabled=True,
        source_selection_mode=SourceSelectionMode.FROM_ORDER,
    )
    config_dict: dict = config.model_dump()

    # Assert
    assert "source_selection_mode" in config_dict
    assert config_dict["source_selection_mode"] == "FROM_ORDER"
    assert "reference_pattern" in config_dict
    assert "prompts_config" in config_dict


@pytest.mark.ai
def test_hallucination_metric_default_config__exists__as_module_constant() -> None:
    """
    Purpose: Verify that hallucination_metric_default_config constant exists.
    Why this matters: Provides easy access to default configuration.
    Setup summary: Check module constant exists and is not None.
    """
    # Arrange - No setup needed

    # Act & Assert
    assert hallucination_metric_default_config is not None


@pytest.mark.ai
def test_hallucination_metric_default_config__is_hallucination_config_instance__for_type_safety() -> (
    None
):
    """
    Purpose: Verify that default config is an instance of HallucinationConfig.
    Why this matters: Ensures type safety and correct configuration structure.
    Setup summary: Check instance type of module constant.
    """
    # Arrange - No setup needed

    # Act & Assert
    assert isinstance(hallucination_metric_default_config, HallucinationConfig)


@pytest.mark.ai
def test_hallucination_metric_default_config__is_disabled__for_safety() -> None:
    """
    Purpose: Verify that default config has metric disabled.
    Why this matters: Prevents accidental evaluation costs on startup.
    Setup summary: Check enabled field of default config.
    """
    # Arrange - No setup needed

    # Act & Assert
    assert hallucination_metric_default_config.enabled is False


@pytest.mark.ai
def test_hallucination_metric_default_config__has_expected_default_settings__configured() -> (
    None
):
    """
    Purpose: Verify that default config has expected field values.
    Why this matters: Ensures consistent default behavior across deployments.
    Setup summary: Check key configuration fields of default config.
    """
    # Arrange
    config: HallucinationConfig = hallucination_metric_default_config

    # Act & Assert
    assert config.name == EvaluationMetricName.HALLUCINATION
    assert config.source_selection_mode == SourceSelectionMode.FROM_ORIGINAL_RESPONSE
    assert config.reference_pattern == r"[\[<]?source(\d+)[>\]]?"


@pytest.mark.ai
def test_hallucination_required_input_fields__exists__as_list() -> None:
    """
    Purpose: Verify that hallucination_required_input_fields list exists.
    Why this matters: Defines required inputs for hallucination evaluation.
    Setup summary: Check module constant exists and is list type.
    """
    # Arrange - No setup needed

    # Act & Assert
    assert hallucination_required_input_fields is not None
    assert isinstance(hallucination_required_input_fields, list)


@pytest.mark.ai
def test_hallucination_required_input_fields__includes_input_text__as_required() -> (
    None
):
    """
    Purpose: Verify that INPUT_TEXT is in required fields list.
    Why this matters: Input text is essential for hallucination detection.
    Setup summary: Check INPUT_TEXT enum value in required fields.
    """
    # Arrange - No setup needed

    # Act & Assert
    assert (
        EvaluationMetricInputFieldName.INPUT_TEXT in hallucination_required_input_fields
    )


@pytest.mark.ai
def test_hallucination_required_input_fields__includes_context_texts__as_required() -> (
    None
):
    """
    Purpose: Verify that CONTEXT_TEXTS is in required fields list.
    Why this matters: Context texts provide grounding source for hallucination check.
    Setup summary: Check CONTEXT_TEXTS enum value in required fields.
    """
    # Arrange - No setup needed

    # Act & Assert
    assert (
        EvaluationMetricInputFieldName.CONTEXT_TEXTS
        in hallucination_required_input_fields
    )


@pytest.mark.ai
def test_hallucination_required_input_fields__includes_history_messages__as_required() -> (
    None
):
    """
    Purpose: Verify that HISTORY_MESSAGES is in required fields list.
    Why this matters: Message history provides conversation context for evaluation.
    Setup summary: Check HISTORY_MESSAGES enum value in required fields.
    """
    # Arrange - No setup needed

    # Act & Assert
    assert (
        EvaluationMetricInputFieldName.HISTORY_MESSAGES
        in hallucination_required_input_fields
    )


@pytest.mark.ai
def test_hallucination_required_input_fields__includes_output_text__as_required() -> (
    None
):
    """
    Purpose: Verify that OUTPUT_TEXT is in required fields list.
    Why this matters: Output text is the target of hallucination evaluation.
    Setup summary: Check OUTPUT_TEXT enum value in required fields.
    """
    # Arrange - No setup needed

    # Act & Assert
    assert (
        EvaluationMetricInputFieldName.OUTPUT_TEXT
        in hallucination_required_input_fields
    )


@pytest.mark.ai
def test_hallucination_required_input_fields__has_four_fields__for_complete_evaluation() -> (
    None
):
    """
    Purpose: Verify that required fields list contains exactly 4 fields.
    Why this matters: Hallucination evaluation requires all 4 input components.
    Setup summary: Check length of required fields list.
    """
    # Arrange - No setup needed

    # Act & Assert
    assert len(hallucination_required_input_fields) == 4


@pytest.mark.ai
def test_hallucination_required_input_fields__contains_only_valid_enum_values__for_type_safety() -> (
    None
):
    """
    Purpose: Verify that all fields are valid EvaluationMetricInputFieldName enum values.
    Why this matters: Ensures type safety and prevents invalid field references.
    Setup summary: Iterate fields, assert each is enum instance.
    """
    # Arrange - No setup needed

    # Act & Assert
    for field in hallucination_required_input_fields:
        assert isinstance(field, EvaluationMetricInputFieldName)
