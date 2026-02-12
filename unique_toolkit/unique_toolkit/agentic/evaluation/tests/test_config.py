"""Tests for evaluation config module."""

import pytest

from unique_toolkit.agentic.evaluation.config import (
    EvaluationMetricConfig,
    EvaluationMetricPromptsConfig,
)
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.language_model.default_language_model import DEFAULT_LANGUAGE_MODEL
from unique_toolkit.language_model.infos import LanguageModelInfo


@pytest.mark.ai
def test_evaluation_metric_prompts_config__initializes_with_empty_strings__by_default() -> (
    None
):
    """
    Purpose: Verify that EvaluationMetricPromptsConfig initializes with empty template strings.
    Why this matters: Default initialization should not load templates automatically.
    Setup summary: Create config with no arguments, assert empty string defaults.
    """
    # Arrange - No setup needed

    # Act
    config: EvaluationMetricPromptsConfig = EvaluationMetricPromptsConfig()

    # Assert
    assert config.system_prompt_template == ""
    assert config.user_prompt_template == ""


@pytest.mark.ai
def test_evaluation_metric_prompts_config__accepts_custom_templates__on_initialization() -> (
    None
):
    """
    Purpose: Verify that EvaluationMetricPromptsConfig accepts custom template values.
    Why this matters: Allows customization of prompts for different evaluation scenarios.
    Setup summary: Initialize with custom prompts, assert they are stored correctly.
    """
    # Arrange
    system_prompt: str = "Custom system prompt"
    user_prompt: str = "Custom user prompt"

    # Act
    config: EvaluationMetricPromptsConfig = EvaluationMetricPromptsConfig(
        system_prompt_template=system_prompt,
        user_prompt_template=user_prompt,
    )

    # Assert
    assert config.system_prompt_template == system_prompt
    assert config.user_prompt_template == user_prompt


@pytest.mark.ai
def test_evaluation_metric_prompts_config__stores_strings__for_template_fields() -> (
    None
):
    """
    Purpose: Verify that prompt template fields accept and store string values.
    Why this matters: Type safety for prompt templates is critical for rendering.
    Setup summary: Create config with string prompts, assert type is string.
    """
    # Arrange
    system_template: str = "Test system prompt"
    user_template: str = "Test user prompt"

    # Act
    config: EvaluationMetricPromptsConfig = EvaluationMetricPromptsConfig(
        system_prompt_template=system_template,
        user_prompt_template=user_template,
    )

    # Assert
    assert isinstance(config.system_prompt_template, str)
    assert isinstance(config.user_prompt_template, str)


@pytest.mark.ai
def test_evaluation_metric_prompts_config__allows_modification__after_initialization() -> (
    None
):
    """
    Purpose: Verify that prompt config fields can be modified after creation.
    Why this matters: Enables dynamic prompt updates during runtime.
    Setup summary: Create config, modify fields, assert new values.
    """
    # Arrange
    config: EvaluationMetricPromptsConfig = EvaluationMetricPromptsConfig()

    # Act
    config.system_prompt_template = "New system prompt"
    config.user_prompt_template = "New user prompt"

    # Assert
    assert config.system_prompt_template == "New system prompt"
    assert config.user_prompt_template == "New user prompt"


@pytest.mark.ai
def test_evaluation_metric_config__initializes_with_default_prompts_config__when_not_provided() -> (
    None
):
    """
    Purpose: Verify that EvaluationMetricConfig creates default prompts config.
    Why this matters: Ensures config is always in valid state even without explicit prompts.
    Setup summary: Create config without prompts_config, assert default empty prompts.
    """
    # Arrange - No setup needed

    # Act
    config: EvaluationMetricConfig = EvaluationMetricConfig(
        enabled=True,
        name=EvaluationMetricName.CONTEXT_RELEVANCY,
    )

    # Assert
    assert isinstance(config.prompts_config, EvaluationMetricPromptsConfig)
    assert config.prompts_config.system_prompt_template == ""
    assert config.prompts_config.user_prompt_template == ""


@pytest.mark.ai
def test_evaluation_metric_config__accepts_custom_prompts_config__on_initialization() -> (
    None
):
    """
    Purpose: Verify that EvaluationMetricConfig accepts custom prompts configuration.
    Why this matters: Allows full customization of evaluation prompts per metric.
    Setup summary: Create custom prompts config, pass to metric config, assert values.
    """
    # Arrange
    prompts_config: EvaluationMetricPromptsConfig = EvaluationMetricPromptsConfig(
        system_prompt_template="Custom system",
        user_prompt_template="Custom user",
    )

    # Act
    config: EvaluationMetricConfig = EvaluationMetricConfig(
        enabled=True,
        name=EvaluationMetricName.CONTEXT_RELEVANCY,
        prompts_config=prompts_config,
    )

    # Assert
    assert config.prompts_config.system_prompt_template == "Custom system"
    assert config.prompts_config.user_prompt_template == "Custom user"


@pytest.mark.ai
def test_evaluation_metric_config__has_all_required_fields__on_initialization() -> None:
    """
    Purpose: Verify that EvaluationMetricConfig has all expected configuration fields.
    Why this matters: Ensures complete config structure for evaluation metrics.
    Setup summary: Create config with language model, assert all fields exist.
    """
    # Arrange
    language_model: LanguageModelInfo = LanguageModelInfo.from_name(DEFAULT_LANGUAGE_MODEL)

    # Act
    config: EvaluationMetricConfig = EvaluationMetricConfig(
        enabled=True,
        name=EvaluationMetricName.HALLUCINATION,
        language_model=language_model,
    )

    # Assert
    assert hasattr(config, "enabled")
    assert hasattr(config, "name")
    assert hasattr(config, "language_model")
    assert hasattr(config, "additional_llm_options")
    assert hasattr(config, "prompts_config")
    assert hasattr(config, "score_to_label")
    assert hasattr(config, "score_to_title")


@pytest.mark.ai
def test_evaluation_metric_config__defaults_to_empty_dict__for_additional_llm_options() -> (
    None
):
    """
    Purpose: Verify that additional_llm_options defaults to empty dictionary.
    Why this matters: Provides safe default for optional LLM configuration.
    Setup summary: Create config without options, assert empty dict default.
    """
    # Arrange - No setup needed

    # Act
    config: EvaluationMetricConfig = EvaluationMetricConfig(
        enabled=True,
        name=EvaluationMetricName.CONTEXT_RELEVANCY,
    )

    # Assert
    assert config.additional_llm_options == {}
    assert isinstance(config.additional_llm_options, dict)


@pytest.mark.ai
def test_evaluation_metric_config__defaults_to_empty_dicts__for_score_mappings() -> (
    None
):
    """
    Purpose: Verify that score mapping dictionaries default to empty.
    Why this matters: Allows optional score labeling and titling per metric.
    Setup summary: Create config without mappings, assert empty dict defaults.
    """
    # Arrange - No setup needed

    # Act
    config: EvaluationMetricConfig = EvaluationMetricConfig(
        enabled=True,
        name=EvaluationMetricName.CONTEXT_RELEVANCY,
    )

    # Assert
    assert config.score_to_label == {}
    assert config.score_to_title == {}


@pytest.mark.ai
def test_evaluation_metric_config__serializes_to_dict__with_all_fields() -> None:
    """
    Purpose: Verify that config can be serialized to dictionary format.
    Why this matters: Required for persistence and API serialization.
    Setup summary: Create config with custom prompts, serialize, assert structure.
    """
    # Arrange
    prompts_config: EvaluationMetricPromptsConfig = EvaluationMetricPromptsConfig(
        system_prompt_template="System",
        user_prompt_template="User",
    )

    # Act
    config: EvaluationMetricConfig = EvaluationMetricConfig(
        enabled=True,
        name=EvaluationMetricName.CONTEXT_RELEVANCY,
        prompts_config=prompts_config,
    )
    config_dict: dict = config.model_dump()

    # Assert
    assert "prompts_config" in config_dict
    assert config_dict["prompts_config"]["system_prompt_template"] == "System"
    assert config_dict["prompts_config"]["user_prompt_template"] == "User"
