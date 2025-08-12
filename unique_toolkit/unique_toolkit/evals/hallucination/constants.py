from typing import Any

from pydantic import Field

from unique_toolkit._common.validators import LMI
from unique_toolkit.evals.config import EvaluationMetricConfig
from unique_toolkit.evals.hallucination.prompts import (
    HALLUCINATION_METRIC_SYSTEM_MSG,
    HALLUCINATION_METRIC_SYSTEM_MSG_DEFAULT,
    HALLUCINATION_METRIC_USER_MSG,
    HALLUCINATION_METRIC_USER_MSG_DEFAULT,
)
from unique_toolkit.evals.schemas import (
    EvaluationMetricInputFieldName,
    EvaluationMetricName,
)


SYSTEM_MSG_KEY = "systemPrompt"
USER_MSG_KEY = "userPrompt"
SYSTEM_MSG_DEFAULT_KEY = "systemPromptDefault"
USER_MSG_DEFAULT_KEY = "userPromptDefault"


class HallucinationConfig(EvaluationMetricConfig):
    enabled: bool = False
    name: EvaluationMetricName = EvaluationMetricName.HALLUCINATION
    language_model: LMI = get_LMI_default_field(DEFAULT_GPT_4o)
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


hallucination_metric_default_config = HallucinationConfig()

hallucination_required_input_fields = [
    EvaluationMetricInputFieldName.INPUT_TEXT,
    EvaluationMetricInputFieldName.CONTEXT_TEXTS,
    EvaluationMetricInputFieldName.HISTORY_MESSAGES,
    EvaluationMetricInputFieldName.OUTPUT_TEXT,
]
