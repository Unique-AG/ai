"""Tests for generation configuration."""

from unique_swot.services.generation.config import ReportGenerationConfig


class TestReportGenerationConfig:
    """Test cases for ReportGenerationConfig class."""

    def test_report_generation_config_default_values(self):
        """Test that ReportGenerationConfig initializes with correct defaults."""
        config = ReportGenerationConfig()

        assert config.batch_size == 3
        assert config.max_tokens_per_batch == 30_000
        assert config.language_model is not None

    def test_report_generation_config_custom_batch_size(self):
        """Test ReportGenerationConfig with custom batch size."""
        config = ReportGenerationConfig(batch_size=10)

        assert config.batch_size == 10

    def test_report_generation_config_custom_max_tokens(self):
        """Test ReportGenerationConfig with custom max tokens."""
        config = ReportGenerationConfig(max_tokens_per_batch=50000)

        assert config.max_tokens_per_batch == 50000

    def test_report_generation_config_all_custom(self):
        """Test ReportGenerationConfig with all custom values."""
        config = ReportGenerationConfig(
            batch_size=5,
            max_tokens_per_batch=20000,
        )

        assert config.batch_size == 5
        assert config.max_tokens_per_batch == 20000

    def test_report_generation_config_serialization(self):
        """Test that ReportGenerationConfig can be serialized."""
        config = ReportGenerationConfig(batch_size=7)
        config_dict = config.model_dump()

        assert config_dict["batch_size"] == 7

        # Recreate from dict
        config_restored = ReportGenerationConfig.model_validate(config_dict)
        assert config_restored.batch_size == 7

    def test_report_generation_config_small_batch_size(self):
        """Test ReportGenerationConfig with small batch size."""
        config = ReportGenerationConfig(batch_size=1)

        assert config.batch_size == 1

    def test_report_generation_config_large_batch_size(self):
        """Test ReportGenerationConfig with large batch size."""
        config = ReportGenerationConfig(batch_size=100)

        assert config.batch_size == 100
