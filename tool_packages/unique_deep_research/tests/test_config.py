"""
Unit tests for config.py module.
"""

import pytest
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName

from unique_deep_research.config import (
    TEMPLATE_DIR,
    TEMPLATE_ENV,
    BaseEngine,
    DeepResearchEngine,
    DeepResearchToolConfig,
    OpenAIEngine,
    UniqueCustomEngineConfig,
    UniqueEngine,
)


@pytest.mark.ai
def test_deep_research_engine__has_correct_values__for_all_engines() -> None:
    """
    Purpose: Verify DeepResearchEngine enum contains expected engine types.
    Why this matters: Ensures all supported research engines are properly defined.
    Setup summary: Check enum values match expected engine names.
    """
    # Arrange & Act
    engines = list(DeepResearchEngine)

    # Assert
    assert DeepResearchEngine.OPENAI in engines
    assert DeepResearchEngine.UNIQUE in engines
    assert len(engines) == 2


@pytest.mark.ai
def test_deep_research_engine__string_values__match_expected() -> None:
    """
    Purpose: Verify DeepResearchEngine string values are correct.
    Why this matters: String values are used in configuration and templates.
    Setup summary: Check string values match expected names.
    """
    # Assert
    assert DeepResearchEngine.OPENAI == "OpenAI"
    assert DeepResearchEngine.UNIQUE == "Unique"


@pytest.mark.ai
def test_unique_custom_engine_config__has_default_values__for_all_fields() -> None:
    """
    Purpose: Verify UniqueCustomEngineConfig has sensible defaults.
    Why this matters: Default values affect research performance and resource usage.
    Setup summary: Create config instance and check default values.
    """
    # Arrange & Act
    config = UniqueCustomEngineConfig()

    # Assert
    assert config.max_parallel_researchers == 5
    assert config.max_research_iterations_lead_researcher == 6
    assert config.max_research_iterations_sub_researcher == 10


@pytest.mark.ai
def test_unique_custom_engine_config__accepts_custom_values__when_provided() -> None:
    """
    Purpose: Verify UniqueCustomEngineConfig accepts custom parameter values.
    Why this matters: Allows customization of research behavior for different use cases.
    Setup summary: Create config with custom values and verify they are set.
    """
    # Arrange & Act
    config = UniqueCustomEngineConfig(
        max_parallel_researchers=3,
        max_research_iterations_lead_researcher=4,
        max_research_iterations_sub_researcher=8,
    )

    # Assert
    assert config.max_parallel_researchers == 3
    assert config.max_research_iterations_lead_researcher == 4
    assert config.max_research_iterations_sub_researcher == 8


@pytest.mark.ai
def test_base_engine__get_type__returns_correct_engine_type() -> None:
    """
    Purpose: Verify BaseEngine.get_type() returns the correct engine type.
    Why this matters: Engine type is used for routing and configuration decisions.
    Setup summary: Create engine instance and verify get_type() returns expected value.
    """
    # Arrange
    lmi = LanguageModelInfo(name=LanguageModelName.AZURE_GPT_4o_2024_1120)

    # Act
    engine = BaseEngine(
        engine_type=DeepResearchEngine.UNIQUE,
        small_model=lmi,
        large_model=lmi,
        research_model=lmi,
    )

    # Assert
    assert engine.get_type() == DeepResearchEngine.UNIQUE


@pytest.mark.ai
def test_unique_engine__has_correct_default_type__for_unique_engine() -> None:
    """
    Purpose: Verify UniqueEngine defaults to UNIQUE engine type.
    Why this matters: Ensures proper engine type assignment for unique research engine.
    Setup summary: Create UniqueEngine instance and verify engine_type.
    """
    # Arrange
    lmi = LanguageModelInfo(name=LanguageModelName.AZURE_GPT_4o_2024_1120)

    # Act
    engine = UniqueEngine(
        small_model=lmi,
        large_model=lmi,
        research_model=lmi,
    )

    # Assert
    assert engine.engine_type == DeepResearchEngine.UNIQUE


@pytest.mark.ai
def test_openai_engine__has_correct_default_type__for_openai_engine() -> None:
    """
    Purpose: Verify OpenAIEngine defaults to OPENAI engine type.
    Why this matters: Ensures proper engine type assignment for OpenAI research engine.
    Setup summary: Create OpenAIEngine instance and verify engine_type.
    """
    # Arrange
    lmi = LanguageModelInfo(name=LanguageModelName.AZURE_GPT_4o_2024_1120)

    # Act
    engine = OpenAIEngine(
        small_model=lmi,
        large_model=lmi,
        research_model=lmi,
    )

    # Assert
    assert engine.engine_type == DeepResearchEngine.OPENAI


@pytest.mark.ai
def test_deep_research_tool_config__has_unique_engine_default__when_no_engine_specified() -> (
    None
):
    """
    Purpose: Verify DeepResearchToolConfig defaults to UniqueEngine.
    Why this matters: Ensures backward compatibility and proper default behavior.
    Setup summary: Create config without specifying engine and verify default.
    """
    # Arrange & Act
    config = DeepResearchToolConfig()

    # Assert
    assert isinstance(config.engine, UniqueEngine)
    assert config.engine.engine_type == DeepResearchEngine.UNIQUE


@pytest.mark.ai
def test_deep_research_tool_config__accepts_custom_engine__when_provided() -> None:
    """
    Purpose: Verify DeepResearchToolConfig accepts custom engine configuration.
    Why this matters: Allows users to choose between different research engines.
    Setup summary: Create config with custom engine and verify it is set correctly.
    """
    # Arrange
    lmi = LanguageModelInfo(name=LanguageModelName.AZURE_GPT_4o_2024_1120)
    custom_engine = OpenAIEngine(
        small_model=lmi,
        large_model=lmi,
        research_model=lmi,
    )

    # Act
    config = DeepResearchToolConfig(engine=custom_engine)

    # Assert
    assert isinstance(config.engine, OpenAIEngine)
    assert config.engine.engine_type == DeepResearchEngine.OPENAI


@pytest.mark.ai
def test_template_dir__exists__and_is_directory() -> None:
    """
    Purpose: Verify TEMPLATE_DIR points to existing templates directory.
    Why this matters: Template directory is required for Jinja2 template loading.
    Setup summary: Check TEMPLATE_DIR exists and is a directory.
    """
    # Assert
    assert TEMPLATE_DIR.exists()
    assert TEMPLATE_DIR.is_dir()


@pytest.mark.ai
def test_template_env__is_configured__with_correct_loader() -> None:
    """
    Purpose: Verify TEMPLATE_ENV is properly configured with FileSystemLoader.
    Why this matters: Template environment is used throughout the application for rendering.
    Setup summary: Check template environment loader configuration.
    """
    # Assert
    assert TEMPLATE_ENV is not None
    assert hasattr(TEMPLATE_ENV, "loader")
    assert str(TEMPLATE_DIR) in str(TEMPLATE_ENV.loader.searchpath)
