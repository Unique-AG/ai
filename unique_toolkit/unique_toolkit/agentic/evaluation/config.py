from typing import Annotated, Any

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit._common.validators import LMI
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationMetricName,
)
from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.language_model.default_language_model import DEFAULT_GPT_4o
from unique_toolkit.language_model.infos import LanguageModelInfo

PromptType = Annotated[str, RJSFMetaTag.StringWidget.textarea(rows=5)]


class EvaluationMetricPromptsConfig(BaseModel):
    model_config = get_configuration_dict()

    system_prompt_template: PromptType = Field(
        default="",
        description="The system prompt for the evaluation metric.",
    )
    user_prompt_template: PromptType = Field(
        default="",
        description="The user prompt for the evaluation metric.",
    )


class EvaluationMetricConfig(BaseToolConfig):
    enabled: SkipJsonSchema[bool] = False
    name: SkipJsonSchema[EvaluationMetricName]
    language_model: LMI = LanguageModelInfo.from_name(
        DEFAULT_GPT_4o,
    )
    additional_llm_options: dict[str, Any] = Field(
        default={},
        description="Additional options to pass to the language model.",
    )
    prompts_config: EvaluationMetricPromptsConfig = Field(
        default_factory=EvaluationMetricPromptsConfig,
        description="The prompts config for the evaluation metric.",
    )
    score_to_label: dict[str, str] = {}
    score_to_title: dict[str, str] = {}
