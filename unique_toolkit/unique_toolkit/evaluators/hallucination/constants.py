from typing import Any

from pydantic import Field
from unique_toolkit.evaluators.config import EvaluationMetricConfig
from unique_toolkit.evaluators.hallucination.prompts import (
    HALLUCINATION_METRIC_SYSTEM_MSG,
    HALLUCINATION_METRIC_SYSTEM_MSG_DEFAULT,
    HALLUCINATION_METRIC_USER_MSG,
    HALLUCINATION_METRIC_USER_MSG_DEFAULT,
)
from unique_toolkit.evaluators.schemas import (
    EvaluationMetricInputFieldName,
    EvaluationMetricName,
)
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelName,
)
from unique_toolkit.unique_toolkit._common.validators import LMI

SYSTEM_MSG_KEY = "systemPrompt"
USER_MSG_KEY = "userPrompt"
SYSTEM_MSG_DEFAULT_KEY = "systemPromptDefault"
USER_MSG_DEFAULT_KEY = "userPromptDefault"


hallucination_metric_default_config = EvaluationMetricConfig(
    enabled=False,
    name=EvaluationMetricName.HALLUCINATION,
    language_model=LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_4_0613),
    score_to_emoji={"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"},
    custom_prompts={
        SYSTEM_MSG_KEY: HALLUCINATION_METRIC_SYSTEM_MSG,
        USER_MSG_KEY: HALLUCINATION_METRIC_USER_MSG,
        SYSTEM_MSG_DEFAULT_KEY: HALLUCINATION_METRIC_SYSTEM_MSG_DEFAULT,
        USER_MSG_DEFAULT_KEY: HALLUCINATION_METRIC_USER_MSG_DEFAULT,
    },
)

hallucination_required_input_fields = [
    EvaluationMetricInputFieldName.INPUT_TEXT,
    EvaluationMetricInputFieldName.CONTEXT_TEXTS,
    EvaluationMetricInputFieldName.HISTORY_MESSAGES,
    EvaluationMetricInputFieldName.OUTPUT_TEXT,
]


class HallucinationConfig(EvaluationMetricConfig):
    enabled: bool = False
    name: EvaluationMetricName = EvaluationMetricName.HALLUCINATION
    language_model: LMI =  LanguageModelInfo.from_name(
        LanguageModelName.AZURE_GPT_4o_2024_1120,
    )
    additional_llm_options: dict[str, Any] = Field(
        default={},
        description="Additional options to pass to the language model.",
    )
    custom_prompts: dict = {
        SYSTEM_MSG_KEY: HALLUCINATION_METRIC_SYSTEM_MSG,
        USER_MSG_KEY: HALLUCINATION_METRIC_USER_MSG,
        SYSTEM_MSG_DEFAULT_KEY: HALLUCINATION_METRIC_SYSTEM_MSG_DEFAULT,
        USER_MSG_DEFAULT_KEY: HALLUCINATION_METRIC_USER_MSG_DEFAULT,
    }
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