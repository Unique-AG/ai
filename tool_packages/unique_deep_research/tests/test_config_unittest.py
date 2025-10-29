"""
Simple unittest tests for config.py module.
"""

import unittest

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


class TestConfig(unittest.TestCase):
    """Test cases for config.py module."""

    def test_deep_research_engine_has_correct_values(self):
        """Test that DeepResearchEngine enum contains expected engine types."""
        engines = list(DeepResearchEngine)

        self.assertIn(DeepResearchEngine.OPENAI, engines)
        self.assertIn(DeepResearchEngine.UNIQUE, engines)
        self.assertEqual(len(engines), 2)

    def test_deep_research_engine_string_values(self):
        """Test that DeepResearchEngine string values are correct."""
        self.assertEqual(DeepResearchEngine.OPENAI, "OpenAI")
        self.assertEqual(DeepResearchEngine.UNIQUE, "Unique")

    def test_unique_custom_engine_config_default_values(self):
        """Test that UniqueCustomEngineConfig has sensible defaults."""
        config = UniqueCustomEngineConfig()

        self.assertEqual(config.max_parallel_researchers, 5)
        self.assertEqual(config.max_research_iterations_lead_researcher, 6)
        self.assertEqual(config.max_research_iterations_sub_researcher, 10)

    def test_unique_custom_engine_config_custom_values(self):
        """Test that UniqueCustomEngineConfig accepts custom parameter values."""
        config = UniqueCustomEngineConfig(
            max_parallel_researchers=3,
            max_research_iterations_lead_researcher=4,
            max_research_iterations_sub_researcher=8,
        )

        self.assertEqual(config.max_parallel_researchers, 3)
        self.assertEqual(config.max_research_iterations_lead_researcher, 4)
        self.assertEqual(config.max_research_iterations_sub_researcher, 8)

    def test_base_engine_get_type(self):
        """Test that BaseEngine.get_type() returns the correct engine type."""
        # Arrange
        small_model = LanguageModelInfo(name=LanguageModelName.AZURE_GPT_4o_2024_1120)
        large_model = LanguageModelInfo(name=LanguageModelName.AZURE_GPT_4o_2024_1120)
        research_model = LanguageModelInfo(
            name=LanguageModelName.AZURE_GPT_4o_2024_1120
        )

        # Act
        engine = BaseEngine(
            engine_type=DeepResearchEngine.UNIQUE,
            small_model=small_model,
            large_model=large_model,
            research_model=research_model,
        )

        # Assert
        self.assertEqual(engine.get_type(), DeepResearchEngine.UNIQUE)

    def test_unique_engine_default_type(self):
        """Test that UniqueEngine defaults to UNIQUE engine type."""
        # Arrange
        lmi = LanguageModelInfo(name=LanguageModelName.AZURE_GPT_4o_2024_1120)

        # Act
        engine = UniqueEngine(
            small_model=lmi,
            large_model=lmi,
            research_model=lmi,
        )

        # Assert
        self.assertEqual(engine.engine_type, DeepResearchEngine.UNIQUE)

    def test_openai_engine_default_type(self):
        """Test that OpenAIEngine defaults to OPENAI engine type."""
        # Arrange
        lmi = LanguageModelInfo(name=LanguageModelName.AZURE_GPT_4o_2024_1120)

        # Act
        engine = OpenAIEngine(
            small_model=lmi,
            large_model=lmi,
            research_model=lmi,
        )

        # Assert
        self.assertEqual(engine.engine_type, DeepResearchEngine.OPENAI)

    def test_deep_research_tool_config_default_engine(self):
        """Test that DeepResearchToolConfig defaults to UniqueEngine."""
        config = DeepResearchToolConfig()

        self.assertIsInstance(config.engine, UniqueEngine)
        self.assertEqual(config.engine.engine_type, DeepResearchEngine.UNIQUE)

    def test_deep_research_tool_config_custom_engine(self):
        """Test that DeepResearchToolConfig accepts custom engine configuration."""
        # Arrange
        small_model = LanguageModelInfo(name=LanguageModelName.AZURE_GPT_4o_2024_1120)
        large_model = LanguageModelInfo(name=LanguageModelName.AZURE_GPT_4o_2024_1120)
        research_model = LanguageModelInfo(
            name=LanguageModelName.AZURE_GPT_4o_2024_1120
        )
        custom_engine = OpenAIEngine(
            small_model=small_model,
            large_model=large_model,
            research_model=research_model,
        )

        # Act
        config = DeepResearchToolConfig(engine=custom_engine)

        # Assert
        self.assertIsInstance(config.engine, OpenAIEngine)
        self.assertEqual(config.engine.engine_type, DeepResearchEngine.OPENAI)

    def test_template_dir_exists(self):
        """Test that TEMPLATE_DIR points to existing templates directory."""
        self.assertTrue(TEMPLATE_DIR.exists())
        self.assertTrue(TEMPLATE_DIR.is_dir())

    def test_template_env_configured(self):
        """Test that TEMPLATE_ENV is properly configured with FileSystemLoader."""
        self.assertIsNotNone(TEMPLATE_ENV)
        self.assertTrue(hasattr(TEMPLATE_ENV, "loader"))


if __name__ == "__main__":
    unittest.main()
