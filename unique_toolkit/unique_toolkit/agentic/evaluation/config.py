from typing import Any

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema

from unique_toolkit._common.validators import LMI
from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.language_model.default_language_model import DEFAULT_GPT_4o
from unique_toolkit.language_model.infos import LanguageModelInfo

from .schemas import (
    EvaluationMetricName,
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
    custom_prompts: dict[str, str] = {}
    score_to_label: dict[str, str] = {}
    score_to_title: dict[str, str] = {}
