from enum import StrEnum
from typing import Any

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema

from unique_toolkit._common.validators import LMI
from unique_toolkit.agentic.evaluation.config import (
    EvaluationMetricConfig,
    EvaluationMetricPromptsConfig,
    PromptType,
)
from unique_toolkit.agentic.evaluation.hallucination.prompts import (
    system_prompt_loader,
    user_prompt_loader,
)
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationMetricInputFieldName,
    EvaluationMetricName,
)
from unique_toolkit.language_model.default_language_model import DEFAULT_GPT_4o
from unique_toolkit.language_model.infos import LanguageModelInfo


class SourceSelectionMode(StrEnum):
    FROM_IDS = "FROM_IDS"
    FROM_ORDER = "FROM_ORDER"
    FROM_ORIGINAL_RESPONSE = "FROM_ORIGINAL_RESPONSE"


class HallucinationPromptsConfig(EvaluationMetricPromptsConfig):
    system_prompt_template: PromptType = Field(default_factory=system_prompt_loader)
    user_prompt_template: PromptType = Field(default_factory=user_prompt_loader)


class HallucinationConfig(EvaluationMetricConfig):
    source_selection_mode: SourceSelectionMode = Field(
        default=SourceSelectionMode.FROM_ORIGINAL_RESPONSE
    )
    ref_pattern: str = Field(default=r"[\[<]?source(\d+)[>\]]?")
    enabled: SkipJsonSchema[bool] = False
    name: SkipJsonSchema[EvaluationMetricName] = EvaluationMetricName.HALLUCINATION
    language_model: LMI = LanguageModelInfo.from_name(
        DEFAULT_GPT_4o,
    )
    prompts_config: HallucinationPromptsConfig = Field(  # type: ignore[assignment]
        default_factory=HallucinationPromptsConfig,
        description="The prompts config for the hallucination metric",
    )
    additional_llm_options: dict[str, Any] = Field(
        default={},
        description="Additional options to pass to the language model.",
    )
    score_to_label: dict = {
        "LOW": "GREEN",
        "MEDIUM": "YELLOW",
        "HIGH": "RED",
    }
    score_to_title: dict = {
        "LOW": "No Hallucination Detected",
        "MEDIUM": "Hallucination Warning",
        "HIGH": "High Hallucination",
    }


hallucination_metric_default_config = HallucinationConfig()

hallucination_required_input_fields = [
    EvaluationMetricInputFieldName.INPUT_TEXT,
    EvaluationMetricInputFieldName.CONTEXT_TEXTS,
    EvaluationMetricInputFieldName.HISTORY_MESSAGES,
    EvaluationMetricInputFieldName.OUTPUT_TEXT,
]
