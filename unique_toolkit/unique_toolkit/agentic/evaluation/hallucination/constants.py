from typing import Any

from pydantic import Field

from unique_toolkit._common.validators import LMI
from unique_toolkit.agentic.evaluation.config import (
    CustomPrompts,
    EvaluationMetricConfig,
    ScoreMapping,
)
from unique_toolkit.agentic.evaluation.hallucination.prompts import (
    HALLUCINATION_METRIC_SYSTEM_MSG,
    HALLUCINATION_METRIC_SYSTEM_MSG_DEFAULT,
    HALLUCINATION_METRIC_USER_MSG,
    HALLUCINATION_METRIC_USER_MSG_DEFAULT,
)
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationMetricInputFieldName,
    EvaluationMetricName,
)
from unique_toolkit.language_model.default_language_model import DEFAULT_GPT_4o
from unique_toolkit.language_model.infos import LanguageModelInfo

SYSTEM_MSG_KEY = "systemPrompt"
USER_MSG_KEY = "userPrompt"
SYSTEM_MSG_DEFAULT_KEY = "systemPromptDefault"
USER_MSG_DEFAULT_KEY = "userPromptDefault"


class HallucinationConfig(EvaluationMetricConfig):
    enabled: bool = False
    name: EvaluationMetricName = EvaluationMetricName.HALLUCINATION
    language_model: LMI = LanguageModelInfo.from_name(
        DEFAULT_GPT_4o,
    )
    additional_llm_options: dict[str, Any] = Field(
        default={},
        description="Additional options to pass to the language model.",
    )
    custom_prompts: CustomPrompts | dict[str, str] = Field(
        default_factory=lambda: CustomPrompts(
            system_prompt=HALLUCINATION_METRIC_SYSTEM_MSG,
            user_prompt=HALLUCINATION_METRIC_USER_MSG,
            system_prompt_default=HALLUCINATION_METRIC_SYSTEM_MSG_DEFAULT,
            user_prompt_default=HALLUCINATION_METRIC_USER_MSG_DEFAULT,
        )
    )
    score_to_label: ScoreMapping | dict[str, str] = Field(
        default_factory=lambda: ScoreMapping(
            low="GREEN",
            medium="YELLOW",
            high="RED",
        )
    )
    score_to_title: ScoreMapping | dict[str, str] = Field(
        default_factory=lambda: ScoreMapping(
            low="No Hallucination Detected",
            medium="Hallucination Warning",
            high="High Hallucination",
        )
    )


hallucination_metric_default_config = HallucinationConfig()

hallucination_required_input_fields = [
    EvaluationMetricInputFieldName.INPUT_TEXT,
    EvaluationMetricInputFieldName.CONTEXT_TEXTS,
    EvaluationMetricInputFieldName.HISTORY_MESSAGES,
    EvaluationMetricInputFieldName.OUTPUT_TEXT,
]
