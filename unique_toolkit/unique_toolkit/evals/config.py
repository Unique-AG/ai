from typing import Any

from humps import camelize
from pydantic import BaseModel, ConfigDict, Field

from unique_toolkit._common.validators import LMI
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName


from .schemas import (
    EvaluationMetricName,
)

model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
    arbitrary_types_allowed=True,
    validate_default=True,
)


class EvaluationMetricConfig(BaseModel):
    model_config = model_config

    enabled: bool = False
    name: EvaluationMetricName
    language_model: LMI = LanguageModelInfo.from_name(
        LanguageModelName.AZURE_GPT_35_TURBO_0125,
    )
    additional_llm_options: dict[str, Any] = Field(
        default={},
        description="Additional options to pass to the language model.",
    )
    custom_prompts: dict[str, str] = {}
    score_to_label: dict[str, str] = {}
    score_to_title: dict[str, str] = {}
