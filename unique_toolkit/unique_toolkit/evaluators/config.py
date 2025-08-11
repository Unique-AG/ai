from humps import camelize
from pydantic import BaseModel, ConfigDict

from unique_toolkit._common.validators import LMI, LanguageModelInfo
from unique_toolkit.evaluators.schemas import (
    EvaluationMetricName,
)
from unique_toolkit.language_model.infos import (
    LanguageModelName,
)


class EvaluationMetricConfig(BaseModel):
    model_config = ConfigDict(
        alias_generator=camelize,
        populate_by_name=True,
        validate_default=True,
    )

    enabled: bool = False
    name: EvaluationMetricName
    language_model: LMI = LanguageModelInfo.from_name(
        LanguageModelName.AZURE_GPT_35_TURBO_0125,
    )
    custom_prompts: dict[str, str] = {}
    score_to_emoji: dict[str, str] = {}
    score_to_label: dict[str, str] = {}
    score_to_title: dict[str, str] = {}
