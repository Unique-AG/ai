"""
Test backward compatibility for evaluation configs.
This ensures that both dict-based configs (old format) and new schema-based configs work correctly.
"""

import pytest

from unique_toolkit.agentic.evaluation.config import (
    CustomPrompts,
    EvaluationMetricConfig,
    ScoreMapping,
)
from unique_toolkit.agentic.evaluation.hallucination.constants import (
    HallucinationConfig,
)
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.language_model.default_language_model import DEFAULT_GPT_4o
from unique_toolkit.language_model.infos import LanguageModelInfo


class TestCustomPromptsBackwardCompatibility:
    """Test CustomPrompts model backward compatibility."""

    def test_custom_prompts_model_creation(self):
        """Test creating CustomPrompts model with all fields."""
        prompts = CustomPrompts(
            system_prompt="System message",
            user_prompt="User message",
            system_prompt_default="Default system",
            user_prompt_default="Default user",
        )

        assert prompts.system_prompt == "System message"
        assert prompts.user_prompt == "User message"
        assert prompts.system_prompt_default == "Default system"
        assert prompts.user_prompt_default == "Default user"

    def test_custom_prompts_from_dict(self):
        """Test creating CustomPrompts model from dict."""
        data = {
            "systemPrompt": "System message",
            "userPrompt": "User message",
            "systemPromptDefault": "Default system",
            "userPromptDefault": "Default user",
        }
        prompts = CustomPrompts.from_dict(data)

        assert prompts.system_prompt == "System message"
        assert prompts.user_prompt == "User message"
        assert prompts.system_prompt_default == "Default system"
        assert prompts.user_prompt_default == "Default user"

    def test_custom_prompts_empty_dict(self):
        """Test creating CustomPrompts from empty dict."""
        prompts = CustomPrompts.from_dict({})

        assert prompts.system_prompt == ""
        assert prompts.user_prompt == ""
        assert prompts.system_prompt_default == ""
        assert prompts.user_prompt_default == ""


class TestScoreMappingBackwardCompatibility:
    """Test ScoreMapping model backward compatibility."""

    def test_score_mapping_model_creation(self):
        """Test creating ScoreMapping model with all fields."""
        mapping = ScoreMapping(
            low="GREEN",
            medium="YELLOW",
            high="RED",
        )

        assert mapping.low == "GREEN"
        assert mapping.medium == "YELLOW"
        assert mapping.high == "RED"

    def test_score_mapping_from_dict(self):
        """Test creating ScoreMapping model from dict."""
        data = {
            "LOW": "GREEN",
            "MEDIUM": "YELLOW",
            "HIGH": "RED",
        }
        mapping = ScoreMapping.from_dict(data)

        assert mapping.low == "GREEN"
        assert mapping.medium == "YELLOW"
        assert mapping.high == "RED"

    def test_score_mapping_empty_dict(self):
        """Test creating ScoreMapping from empty dict."""
        mapping = ScoreMapping.from_dict({})

        assert mapping.low == ""
        assert mapping.medium == ""
        assert mapping.high == ""


class TestEvaluationMetricConfigBackwardCompatibility:
    """Test EvaluationMetricConfig with dict and model formats."""

    def test_config_with_dict_custom_prompts(self):
        """Test creating config with dict-based custom_prompts (old format)."""
        config = EvaluationMetricConfig(
            name=EvaluationMetricName.HALLUCINATION,
            custom_prompts={
                "systemPrompt": "System",
                "userPrompt": "User",
                "systemPromptDefault": "Default System",
                "userPromptDefault": "Default User",
            },
        )

        # Should be converted to CustomPrompts model
        assert isinstance(config.custom_prompts, CustomPrompts)
        assert config.custom_prompts.system_prompt == "System"
        assert config.custom_prompts.user_prompt == "User"

    def test_config_with_model_custom_prompts(self):
        """Test creating config with CustomPrompts model (new format)."""
        prompts = CustomPrompts(
            system_prompt="System",
            user_prompt="User",
            system_prompt_default="Default System",
            user_prompt_default="Default User",
        )
        config = EvaluationMetricConfig(
            name=EvaluationMetricName.HALLUCINATION,
            custom_prompts=prompts,
        )

        assert isinstance(config.custom_prompts, CustomPrompts)
        assert config.custom_prompts.system_prompt == "System"

    def test_config_with_dict_score_mappings(self):
        """Test creating config with dict-based score mappings (old format)."""
        config = EvaluationMetricConfig(
            name=EvaluationMetricName.HALLUCINATION,
            score_to_label={"LOW": "GREEN", "MEDIUM": "YELLOW", "HIGH": "RED"},
            score_to_title={
                "LOW": "No Issue",
                "MEDIUM": "Warning",
                "HIGH": "Critical",
            },
        )

        # Should be converted to ScoreMapping model
        assert isinstance(config.score_to_label, ScoreMapping)
        assert isinstance(config.score_to_title, ScoreMapping)
        assert config.score_to_label.low == "GREEN"
        assert config.score_to_title.high == "Critical"

    def test_config_with_model_score_mappings(self):
        """Test creating config with ScoreMapping model (new format)."""
        label_mapping = ScoreMapping(low="GREEN", medium="YELLOW", high="RED")
        title_mapping = ScoreMapping(
            low="No Issue", medium="Warning", high="Critical"
        )
        config = EvaluationMetricConfig(
            name=EvaluationMetricName.HALLUCINATION,
            score_to_label=label_mapping,
            score_to_title=title_mapping,
        )

        assert isinstance(config.score_to_label, ScoreMapping)
        assert isinstance(config.score_to_title, ScoreMapping)
        assert config.score_to_label.low == "GREEN"

    def test_config_default_values(self):
        """Test config with default values."""
        config = EvaluationMetricConfig(name=EvaluationMetricName.HALLUCINATION)

        assert isinstance(config.custom_prompts, CustomPrompts)
        assert isinstance(config.score_to_label, ScoreMapping)
        assert isinstance(config.score_to_title, ScoreMapping)
        assert config.additional_llm_options == {}


class TestHallucinationConfigBackwardCompatibility:
    """Test HallucinationConfig specifically."""

    def test_hallucination_config_defaults(self):
        """Test HallucinationConfig has proper default values."""
        config = HallucinationConfig()

        assert config.enabled is False
        assert config.name == EvaluationMetricName.HALLUCINATION
        assert isinstance(config.custom_prompts, CustomPrompts)
        assert isinstance(config.score_to_label, ScoreMapping)
        assert isinstance(config.score_to_title, ScoreMapping)

        # Check that defaults are set correctly
        assert config.score_to_label.low == "GREEN"
        assert config.score_to_label.medium == "YELLOW"
        assert config.score_to_label.high == "RED"

        assert config.score_to_title.low == "No Hallucination Detected"
        assert config.score_to_title.medium == "Hallucination Warning"
        assert config.score_to_title.high == "High Hallucination"

    def test_hallucination_config_with_dict_override(self):
        """Test overriding HallucinationConfig with dict values."""
        config = HallucinationConfig(
            custom_prompts={
                "systemPrompt": "Custom System",
                "userPrompt": "Custom User",
            },
            score_to_label={"LOW": "BLUE", "MEDIUM": "ORANGE", "HIGH": "PURPLE"},
        )

        assert isinstance(config.custom_prompts, CustomPrompts)
        assert isinstance(config.score_to_label, ScoreMapping)

    def test_hallucination_config_model_validation(self):
        """Test that HallucinationConfig validates correctly."""
        config = HallucinationConfig(
            enabled=True,
            language_model=LanguageModelInfo.from_name(DEFAULT_GPT_4o),
        )

        assert config.enabled is True
        assert config.language_model.name == DEFAULT_GPT_4o


class TestJSONSchemaCompatibility:
    """Test that configs generate proper JSON schemas for react-schema-forms."""

    def test_custom_prompts_schema(self):
        """Test CustomPrompts generates proper JSON schema."""
        schema = CustomPrompts.model_json_schema()

        assert "properties" in schema
        assert "systemPrompt" in schema["properties"]
        assert "userPrompt" in schema["properties"]
        assert "systemPromptDefault" in schema["properties"]
        assert "userPromptDefault" in schema["properties"]

        # Check that fields have proper types
        assert schema["properties"]["systemPrompt"]["type"] == "string"
        assert schema["properties"]["userPrompt"]["type"] == "string"

    def test_score_mapping_schema(self):
        """Test ScoreMapping generates proper JSON schema."""
        schema = ScoreMapping.model_json_schema()

        assert "properties" in schema
        assert "low" in schema["properties"]
        assert "medium" in schema["properties"]
        assert "high" in schema["properties"]

        # Check that fields have proper types
        assert schema["properties"]["low"]["type"] == "string"
        assert schema["properties"]["medium"]["type"] == "string"
        assert schema["properties"]["high"]["type"] == "string"

    def test_evaluation_metric_config_schema(self):
        """Test EvaluationMetricConfig generates proper JSON schema."""
        schema = EvaluationMetricConfig.model_json_schema()

        assert "properties" in schema
        assert "customPrompts" in schema["properties"]
        assert "scoreToLabel" in schema["properties"]
        assert "scoreToTitle" in schema["properties"]

        # Schemas should not use additionalProperties: true without explicit properties
        # This is checked by verifying that properties are explicitly defined
        custom_prompts_def = schema["properties"]["customPrompts"]
        assert "anyOf" in custom_prompts_def or "$ref" in custom_prompts_def

    def test_hallucination_config_schema(self):
        """Test HallucinationConfig generates proper JSON schema."""
        schema = HallucinationConfig.model_json_schema()

        assert "properties" in schema
        # Check that inherited fields are present
        assert "enabled" in schema["properties"]
        assert "name" in schema["properties"]
        assert "customPrompts" in schema["properties"]
        assert "scoreToLabel" in schema["properties"]
        assert "scoreToTitle" in schema["properties"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

