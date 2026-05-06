"""Tests for generation configuration: GenerationMode, ReportGenerationConfig, and prompt configs."""

import pytest

from unique_swot.services.generation.agentic.prompts.cluster_plan.config import (
    ClusterPlanPromptConfig,
)
from unique_swot.services.generation.agentic.prompts.config import AgenticPromptsConfig
from unique_swot.services.generation.config import (
    GenerationMode,
    ReportGenerationConfig,
)


@pytest.mark.ai
def test_generation_mode__has_expected_values() -> None:
    """
    Purpose: Verify GenerationMode enum has INTERLEAVED and EXTRACT_FIRST members.
    Why this matters: Configuration relies on these exact string values for dispatch.
    Setup summary: Check enum members and their string values.
    """
    assert GenerationMode.INTERLEAVED == "interleaved"
    assert GenerationMode.EXTRACT_FIRST == "extract_first"
    assert len(GenerationMode) == 2


@pytest.mark.ai
def test_generation_mode__get_ui_enum_names__returns_labels() -> None:
    """
    Purpose: Verify get_ui_enum_names returns human-readable labels in correct order.
    Why this matters: UI radio widget depends on label order matching enum order.
    Setup summary: Call classmethod, assert label list matches expected.
    """
    names = GenerationMode.get_ui_enum_names()

    assert len(names) == 2
    assert names[0] == "Interleaved (extract + plan per source)"
    assert names[1] == "Extract First (extract all, then plan once)"


@pytest.mark.ai
def test_report_generation_config__defaults_to_interleaved() -> None:
    """
    Purpose: Verify ReportGenerationConfig defaults to INTERLEAVED mode.
    Why this matters: Existing deployments must keep the original behaviour unless explicitly changed.
    Setup summary: Instantiate config with defaults, assert generation_mode.
    """
    config = ReportGenerationConfig()

    assert config.generation_mode == GenerationMode.INTERLEAVED


@pytest.mark.ai
def test_report_generation_config__accepts_extract_first() -> None:
    """
    Purpose: Verify ReportGenerationConfig can be instantiated with EXTRACT_FIRST mode.
    Why this matters: Ensures the new mode is a valid configuration value.
    Setup summary: Instantiate config with extract_first, assert it is stored.
    """
    config = ReportGenerationConfig(generation_mode=GenerationMode.EXTRACT_FIRST)

    assert config.generation_mode == GenerationMode.EXTRACT_FIRST


# =============================================================================
# ClusterPlanPromptConfig
# =============================================================================


@pytest.mark.ai
def test_cluster_plan_prompt_config__loads_defaults() -> None:
    """
    Purpose: Verify ClusterPlanPromptConfig loads template defaults from disk.
    Why this matters: Missing or empty templates would cause rendering failures at runtime.
    Setup summary: Instantiate default config, verify system_prompt and user_prompt are non-empty.
    """
    config = ClusterPlanPromptConfig()

    assert isinstance(config.system_prompt, str)
    assert len(config.system_prompt) > 0
    assert isinstance(config.user_prompt, str)
    assert len(config.user_prompt) > 0


# =============================================================================
# AgenticPromptsConfig
# =============================================================================


@pytest.mark.ai
def test_agentic_prompts_config__has_cluster_plan_field() -> None:
    """
    Purpose: Verify AgenticPromptsConfig includes the cluster_plan_prompt_config field.
    Why this matters: Extract-first mode relies on this config being present.
    Setup summary: Instantiate default config, verify the field type and default.
    """
    config = AgenticPromptsConfig()

    assert hasattr(config, "cluster_plan_prompt_config")
    assert isinstance(config.cluster_plan_prompt_config, ClusterPlanPromptConfig)


@pytest.mark.ai
def test_agentic_prompts_config__all_prompt_fields_present() -> None:
    """
    Purpose: Verify all expected prompt config fields are present in AgenticPromptsConfig.
    Why this matters: Missing fields would cause AttributeError during generation.
    Setup summary: Check that all five config fields exist.
    """
    config = AgenticPromptsConfig()

    assert hasattr(config, "commands_prompt_config")
    assert hasattr(config, "extraction_prompt_config")
    assert hasattr(config, "plan_prompt_config")
    assert hasattr(config, "cluster_plan_prompt_config")
    assert hasattr(config, "definition_prompt_config")
