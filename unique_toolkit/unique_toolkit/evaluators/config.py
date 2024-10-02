from humps import camelize
from pydantic import BaseModel, ConfigDict, field_validator

from unique_toolkit._common.validators import validate_and_init_language_model
from unique_toolkit.evaluators.schemas import (
    EvaluationMetricName,
)
from unique_toolkit.language_model.infos import (
    LanguageModel,
    LanguageModelName,
)

model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
    arbitrary_types_allowed=True,
    validate_default=True,
    json_encoders={LanguageModel: lambda v: v.display_name},
)


class EvaluationMetricConfig(BaseModel):
    model_config = model_config

    enabled: bool = False
    name: EvaluationMetricName
    language_model: LanguageModel = LanguageModel(
        LanguageModelName.AZURE_GPT_35_TURBO_0613
    )
    custom_prompts: dict[str, str] = {}
    score_to_emoji: dict[str, str] = {}

    @field_validator("language_model", mode="before")
    def validate_language_model(cls, value: LanguageModelName | LanguageModel):
        return validate_and_init_language_model(value)
