from typing import Any

from humps import camelize
from pydantic import BaseModel, ConfigDict, Field, field_validator

from unique_toolkit._common.validators import LMI
from unique_toolkit.language_model.default_language_model import DEFAULT_GPT_4o
from unique_toolkit.language_model.infos import LanguageModelInfo

from .schemas import (
    EvaluationMetricName,
)

model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
    arbitrary_types_allowed=True,
    validate_default=True,
)


class CustomPrompts(BaseModel):
    """
    Custom prompts for evaluation metrics.
    This schema explicitly defines the prompt structure for react-schema-forms compatibility.
    """

    model_config = model_config

    system_prompt: str = Field(
        default="",
        description="System message for the evaluation.",
    )
    user_prompt: str = Field(
        default="",
        description="User message template for the evaluation.",
    )
    system_prompt_default: str = Field(
        default="",
        description="Default system message when no context is available.",
    )
    user_prompt_default: str = Field(
        default="",
        description="Default user message template when no context is available.",
    )

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "CustomPrompts":
        """Create from dictionary for backward compatibility."""
        # Support both camelCase (from JSON/frontend) and snake_case
        return cls(
            system_prompt=data.get("systemPrompt") or data.get("system_prompt", ""),
            user_prompt=data.get("userPrompt") or data.get("user_prompt", ""),
            system_prompt_default=data.get("systemPromptDefault") or data.get("system_prompt_default", ""),
            user_prompt_default=data.get("userPromptDefault") or data.get("user_prompt_default", ""),
        )


class ScoreMapping(BaseModel):
    """
    Score to label/title mapping for evaluation metrics.
    This schema explicitly defines the score mapping structure for react-schema-forms compatibility.
    """

    model_config = model_config

    low: str = Field(
        default="",
        description="Label/title for low score.",
    )
    medium: str = Field(
        default="",
        description="Label/title for medium score.",
    )
    high: str = Field(
        default="",
        description="Label/title for high score.",
    )

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "ScoreMapping":
        """Create from dictionary for backward compatibility."""
        return cls(
            low=data.get("LOW", ""),
            medium=data.get("MEDIUM", ""),
            high=data.get("HIGH", ""),
        )


class EvaluationMetricConfig(BaseModel):
    model_config = model_config

    enabled: bool = False
    name: EvaluationMetricName
    language_model: LMI = LanguageModelInfo.from_name(
        DEFAULT_GPT_4o,
    )
    additional_llm_options: dict[str, Any] = Field(
        default={},
        description="Additional options to pass to the language model.",
    )
    custom_prompts: CustomPrompts = Field(
        default_factory=CustomPrompts,
        description="Custom prompts for the evaluation metric.",
    )
    score_to_label: ScoreMapping = Field(
        default_factory=ScoreMapping,
        description="Mapping from score to label (e.g., LOW -> GREEN).",
    )
    score_to_title: ScoreMapping = Field(
        default_factory=ScoreMapping,
        description="Mapping from score to title (e.g., LOW -> No Hallucination).",
    )

    @field_validator("custom_prompts", mode="before")
    @classmethod
    def convert_custom_prompts(cls, v):
        """Convert dict to CustomPrompts model for backward compatibility."""
        if isinstance(v, dict):
            return CustomPrompts.from_dict(v)
        return v

    @field_validator("score_to_label", mode="before")
    @classmethod
    def convert_score_to_label(cls, v):
        """Convert dict to ScoreMapping model for backward compatibility."""
        if isinstance(v, dict):
            return ScoreMapping.from_dict(v)
        return v

    @field_validator("score_to_title", mode="before")
    @classmethod
    def convert_score_to_title(cls, v):
        """Convert dict to ScoreMapping model for backward compatibility."""
        if isinstance(v, dict):
            return ScoreMapping.from_dict(v)
        return v
