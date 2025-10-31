from enum import StrEnum
from typing import Annotated

from humps import camelize
from pydantic import BaseModel, ConfigDict, Field

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

DeactivatedNone = Annotated[
    None,
    Field(title="Deactivated", description="None"),
]


class AdditionalLLMOptions(BaseModel):
    max_tokens: int = Field(
        default=1000,
        description="The maximum number of tokens to generate.",
    )


additional_llm_options: AdditionalLLMOptions | DeactivatedNone = Field(
    default=None,
    description="Additional options to pass to the language model.",
)


class CustomPrompts(BaseModel):
    system_prompt: str
    user_prompt: str


class Scores(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Labels(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class Titles(StrEnum):
    NO_HALLUCINATION_DETECTED = "no hallucination detected"
    HALLUCINATION_WARNING = "hallucination warning"
    HIGH_HALLUCINATION = "high hallucination"


class ScoreToLabel(BaseModel):
    low: Labels = Field(default=Labels.GREEN, description="Score to label mapping.")
    medium: Labels = Field(default=Labels.YELLOW, description="Score to label mapping.")
    high: Labels = Field(default=Labels.RED, description="Score to label mapping.")


class ScoreToTitle(BaseModel):
    low: Titles = Field(
        default=Titles.NO_HALLUCINATION_DETECTED, description="Score to title mapping."
    )
    medium: Titles = Field(
        default=Titles.HALLUCINATION_WARNING, description="Score to title mapping."
    )
    high: Titles = Field(
        default=Titles.HIGH_HALLUCINATION, description="Score to title mapping."
    )


class EvaluationMetricConfig(BaseModel):
    model_config = model_config

    enabled: bool = False
    name: EvaluationMetricName
    language_model: LMI = LanguageModelInfo.from_name(
        DEFAULT_GPT_4o,
    )
    additional_llm_options: AdditionalLLMOptions | DeactivatedNone = Field(
        default=None,
        description="Additional options to pass to the language model.",
    )
    custom_prompts: CustomPrompts = Field(
        default=CustomPrompts(
            system_prompt="",
            user_prompt="",
        ),
        description="Custom prompts.",
    )
    score_to_label: ScoreToLabel = Field(
        default=ScoreToLabel(
            low=Labels.GREEN,
            medium=Labels.YELLOW,
            high=Labels.RED,
        ),
        description="Score to label mapping.",
    )
    score_to_title: ScoreToTitle | DeactivatedNone = Field(
        default=None,
        description="Score to title mapping.",
    )
